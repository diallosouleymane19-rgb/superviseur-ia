# -*- coding: utf-8 -*-
"""
Copie toutes les données de Supabase vers la base PostgreSQL du serveur OVH (bascule).
Lancement sur le serveur :
    sudo docker compose -f /opt/superviseur/deploy/docker-compose.yml exec app python deploy/copier_donnees.py

- Source : Supabase (SUPABASE_URL + SUPABASE_SERVICE_KEY dans secrets.toml) — lecture seule, rien n'y est modifié.
- Cible  : DATABASE_URL (base du serveur). Refuse de copier si la cible contient déjà des comptes,
  sauf avec --remplacer (vide d'abord les tables de la cible).
- Contrôle final : nombre de lignes identique table par table, sinon code de sortie 1.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from psycopg import sql  # noqa: E402

# Ordre imposé par les liens entre tables (un cabinet avant ses membres, un dossier avant ses analyses…)
TABLES = ["smd_cabinets", "users", "clients", "analyses", "smd_invitations",
          "smd_quota_usage", "audit_logs", "chat_sessions", "demo_requests"]
SEQUENCES = ["clients", "analyses", "smd_quota_usage", "audit_logs"]   # identifiants numériques
PAQUET = 500


def _source():
    """Supabase (cas réel) ou, pour un essai, une autre base PostgreSQL (SOURCE_DATABASE_URL)."""
    url_test = os.getenv("SOURCE_DATABASE_URL")
    if url_test:
        from utils.db_postgres import ClientPostgres
        return ClientPostgres(url_test)
    from utils.db_supabase import _load_credentials
    url, cle = _load_credentials()
    if not url or not cle:
        sys.exit("❌ SUPABASE_URL / SUPABASE_SERVICE_KEY absents de secrets.toml : copie impossible.")
    from supabase import create_client
    return create_client(url, cle)


def _cible():
    from utils.db_supabase import _database_url
    from utils.db_postgres import ClientPostgres
    url = _database_url()
    if not url:
        sys.exit("❌ DATABASE_URL absent : ce script doit tourner sur le serveur OVH.")
    return ClientPostgres(url)


def lire_tout(src, table):
    """Toutes les lignes, par paquets, triées par identifiant."""
    lignes, dernier = [], None
    while True:
        q = src.table(table).select("*").order("id").limit(PAQUET)
        if dernier is not None:
            q = q.gt("id", dernier)
        paquet = q.execute().data or []
        lignes += paquet
        if len(paquet) < PAQUET:
            return lignes
        dernier = paquet[-1]["id"]


def main():
    remplacer = "--remplacer" in sys.argv
    src, cib = _source(), _cible()

    deja = cib._lire(sql.SQL("SELECT count(*) AS n FROM users"), [])[0]["n"]
    if deja and not remplacer:
        sys.exit(f"❌ La base du serveur contient déjà {deja} compte(s). Rien n'a été copié.\n"
                 "   Pour l'écraser avec les données de Supabase : relancez avec --remplacer")
    if remplacer:
        cib._lire(sql.SQL("TRUNCATE {} RESTART IDENTITY CASCADE").format(
            sql.SQL(", ").join(sql.Identifier(t) for t in TABLES)), [])
        print("Base du serveur vidée.")

    attendus = {}
    for t in TABLES:
        lignes = lire_tout(src, t)
        attendus[t] = len(lignes)
        for i in range(0, len(lignes), PAQUET):
            cib.table(t).insert(lignes[i:i + PAQUET]).execute()
        print(f"  {t:<16} {len(lignes):>6} ligne(s) copiée(s)")

    for t in SEQUENCES:   # les prochains identifiants repartent après le plus grand copié
        cib._lire(sql.SQL("SELECT setval(pg_get_serial_sequence({}, 'id'), COALESCE(MAX(id), 0) + 1, false) FROM {}")
                  .format(sql.Literal(t), sql.Identifier(t)), [])

    ecarts = []
    for t in TABLES:
        n = cib._lire(sql.SQL("SELECT count(*) AS n FROM {}").format(sql.Identifier(t)), [])[0]["n"]
        if n != attendus[t]:
            ecarts.append(f"{t} : {attendus[t]} attendue(s), {n} trouvée(s)")
    if ecarts:
        print("❌ Écarts :\n  " + "\n  ".join(ecarts))
        sys.exit(1)
    print(f"✅ Copie vérifiée : {sum(attendus.values())} ligne(s), identiques table par table.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Copie interrompue : {e}\n   La base du serveur est peut-être incomplète : "
              "relancez avec --remplacer une fois le problème corrigé.")
        sys.exit(1)
