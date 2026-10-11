# -*- coding: utf-8 -*-
"""
utils/db_postgres.py - SMD Global Consulting LLC
Accès à une base PostgreSQL standard (hébergement OVH, France) avec la même écriture que le client Supabase :

    db.table("clients").select("id, nom").eq("tenant_id", t).order("nom").execute().data

Seules les opérations utilisées par l'application sont prises en charge : select (avec count="exact"),
insert, update, delete, eq, neq, lt, lte, gt, gte, is_ (null), or_ (syntaxe PostgREST simple), order, limit.
Les résultats sont renvoyés comme Supabase les renvoie (JSON) : identifiants UUID et dates en texte.

Secret requis : DATABASE_URL = "postgresql://utilisateur:motdepasse@hote:5432/base"
"""
import datetime as _dt
import decimal
import re
import uuid

from psycopg import sql
from psycopg.types.json import Jsonb

_IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")
_OPS = {"eq": "=", "neq": "<>", "lt": "<", "lte": "<=", "gt": ">", "gte": ">="}


def _nom(x: str) -> sql.Identifier:
    x = x.strip()
    if not _IDENT.match(x):
        raise ValueError(f"Nom de colonne ou de table refusé : {x!r}")
    return sql.Identifier(x)


def _vers_json(v):
    """Valeur PostgreSQL → valeur telle que Supabase la renvoie (JSON)."""
    if isinstance(v, uuid.UUID):
        return str(v)
    if isinstance(v, _dt.datetime):
        return v.isoformat()
    if isinstance(v, (_dt.date, _dt.time)):
        return v.isoformat()
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, list):
        return [_vers_json(x) for x in v]
    return v


def _vers_pg(v, type_colonne: str = ""):
    """Valeur Python → paramètre PostgreSQL : JSON pour les colonnes json/jsonb (et tout dictionnaire),
    tableau PostgreSQL pour les autres listes (ex. text[])."""
    if v is not None and (type_colonne in ("json", "jsonb") or isinstance(v, dict)):
        return Jsonb(v)
    return v


class Reponse:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class Requete:
    def __init__(self, client, table):
        self._client = client
        self._table = table
        self._action = None
        self._colonnes = "*"
        self._compter = False
        self._valeurs = None
        self._conditions = []   # (sql.Composable, [paramètres])
        self._tri = []
        self._limite = None

    # ── Actions ──
    def select(self, colonnes: str = "*", count: str = None):
        self._action, self._colonnes, self._compter = "select", colonnes, count == "exact"
        return self

    def insert(self, valeurs):
        self._action, self._valeurs = "insert", valeurs
        return self

    def update(self, valeurs: dict):
        self._action, self._valeurs = "update", valeurs
        return self

    def delete(self):
        self._action = "delete"
        return self

    # ── Filtres ──
    def _filtre(self, col, op, val):
        self._conditions.append((sql.SQL("{} " + _OPS[op] + " %s").format(_nom(col)), [val]))
        return self

    def eq(self, col, val):
        return self._filtre(col, "eq", val)

    def neq(self, col, val):
        return self._filtre(col, "neq", val)

    def lt(self, col, val):
        return self._filtre(col, "lt", val)

    def lte(self, col, val):
        return self._filtre(col, "lte", val)

    def gt(self, col, val):
        return self._filtre(col, "gt", val)

    def gte(self, col, val):
        return self._filtre(col, "gte", val)

    def is_(self, col, val):
        if str(val).lower() not in ("null", "none"):
            raise ValueError("is_ : seule la valeur « null » est prise en charge")
        self._conditions.append((sql.SQL("{} IS NULL").format(_nom(col)), []))
        return self

    def or_(self, expression: str):
        self._conditions.append(_ou(expression))
        return self

    def order(self, col, desc: bool = False):
        self._tri.append(sql.SQL("{} " + ("DESC" if desc else "ASC")).format(_nom(col)))
        return self

    def limit(self, n: int):
        self._limite = int(n)
        return self

    # ── Exécution ──
    def _where(self):
        if not self._conditions:
            return sql.SQL(""), []
        parties, params = [], []
        for s, p in self._conditions:
            parties.append(s)
            params += p
        return sql.SQL(" WHERE ") + sql.SQL(" AND ").join(parties), params

    def _colonnes_sql(self):
        if self._colonnes.strip() == "*":
            return sql.SQL("*")
        return sql.SQL(", ").join(_nom(c) for c in self._colonnes.split(","))

    def execute(self) -> Reponse:
        t = _nom(self._table)
        where, params = self._where()
        if self._action == "select":
            q = sql.SQL("SELECT {} FROM {}").format(self._colonnes_sql(), t) + where
            if self._tri:
                q += sql.SQL(" ORDER BY ") + sql.SQL(", ").join(self._tri)
            if self._limite is not None:
                q += sql.SQL(" LIMIT {}").format(sql.Literal(self._limite))
            data = self._client._lire(q, params)
            count = None
            if self._compter:
                count = self._client._lire(sql.SQL("SELECT count(*) AS n FROM {}").format(t) + where, params)[0]["n"]
            return Reponse(data, count)
        if self._action == "insert":
            lignes = self._valeurs if isinstance(self._valeurs, list) else [self._valeurs]
            data = []
            for ligne in lignes:
                cols = list(ligne)
                q = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING *").format(
                    t, sql.SQL(", ").join(_nom(c) for c in cols), sql.SQL(", ").join(sql.Placeholder() * len(cols)))
                types = self._client._types(self._table)
                data += self._client._lire(q, [_vers_pg(ligne[c], types.get(c, "")) for c in cols])
            return Reponse(data)
        if self._action == "update":
            if not self._conditions:
                raise ValueError("update sans filtre refusé")
            cols = list(self._valeurs)
            q = sql.SQL("UPDATE {} SET {}").format(
                t, sql.SQL(", ").join(sql.SQL("{} = %s").format(_nom(c)) for c in cols)) + where + sql.SQL(" RETURNING *")
            types = self._client._types(self._table)
            return Reponse(self._client._lire(q, [_vers_pg(self._valeurs[c], types.get(c, "")) for c in cols] + params))
        if self._action == "delete":
            if not self._conditions:
                raise ValueError("delete sans filtre refusé")
            return Reponse(self._client._lire(sql.SQL("DELETE FROM {}").format(t) + where + sql.SQL(" RETURNING *"), params))
        raise ValueError("Requête incomplète : select, insert, update ou delete attendu")


def _decouper(expr: str):
    """Découpe « a,b,and(c,d) » au premier niveau de virgules."""
    parts, niveau, cour = [], 0, ""
    for ch in expr:
        if ch == "(":
            niveau += 1
        elif ch == ")":
            niveau -= 1
        if ch == "," and niveau == 0:
            parts.append(cour)
            cour = ""
        else:
            cour += ch
    if cour:
        parts.append(cour)
    return [p.strip() for p in parts if p.strip()]


def _condition(expr: str):
    """Une condition PostgREST : « col.op.valeur », « and(...) » ou « or(...) »."""
    for mot, lien in (("and(", " AND "), ("or(", " OR ")):
        if expr.startswith(mot) and expr.endswith(")"):
            morceaux = [_condition(p) for p in _decouper(expr[len(mot):-1])]
            return (sql.SQL("(") + sql.SQL(lien).join(m[0] for m in morceaux) + sql.SQL(")"),
                    [x for m in morceaux for x in m[1]])
    col, op, val = expr.split(".", 2)
    if op == "is":
        if val.lower() != "null":
            raise ValueError("is : seule la valeur « null » est prise en charge")
        return sql.SQL("{} IS NULL").format(_nom(col)), []
    if op not in _OPS:
        raise ValueError(f"Opérateur non pris en charge : {op}")
    return sql.SQL("{} " + _OPS[op] + " %s").format(_nom(col)), [val]


def _ou(expression: str):
    morceaux = [_condition(p) for p in _decouper(expression)]
    return (sql.SQL("(") + sql.SQL(" OR ").join(m[0] for m in morceaux) + sql.SQL(")"),
            [x for m in morceaux for x in m[1]])


class ClientPostgres:
    """Client partagé : un réservoir de connexions, en UTC comme Supabase, validation automatique."""

    def __init__(self, url: str):
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        def _configurer(conn):
            conn.execute("SET TIME ZONE 'UTC'")

        self._pool = ConnectionPool(url, min_size=1, max_size=10, open=True, configure=_configurer,
                                    kwargs={"autocommit": True, "row_factory": dict_row}, check=ConnectionPool.check_connection)
        self._cache_types = {}
        import atexit
        atexit.register(self.fermer)

    def fermer(self):
        try:
            self._pool.close()
        except Exception:
            pass

    def _types(self, table: str) -> dict:
        """Type de chaque colonne (udt_name : jsonb, _text, uuid…), mis en cache."""
        if table not in self._cache_types:
            lignes = self._lire(sql.SQL("SELECT column_name, udt_name FROM information_schema.columns "
                                        "WHERE table_schema = 'public' AND table_name = %s"), [table])
            self._cache_types[table] = {l["column_name"]: l["udt_name"] for l in lignes}
        return self._cache_types[table]

    def table(self, nom: str) -> Requete:
        return Requete(self, nom)

    def _lire(self, requete, params):
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(requete, params)
                if cur.description is None:
                    return []
                return [{k: _vers_json(v) for k, v in ligne.items()} for ligne in cur.fetchall()]
