# -*- coding: utf-8 -*-
"""
utils/auth_rbac.py - SMD Consulting
Module RBAC partage : roles, plans, quotas, audit logs.
Compatible PCG France & SYSCOHADA.
"""

import sqlite3
import os
import bcrypt
from datetime import datetime

# --- Chemin DB ---
_IS_CLOUD = bool(
    os.getenv("STREAMLIT_SHARING_MODE")
    or os.getenv("HOME") == "/home/appuser"
)
DB_PATH = "/tmp/smd_users.db" if _IS_CLOUD else "smd_users.db"

# --- Roles ---
ROLES = {
    "admin":         {"label": "Administrateur SMD",  "level": 4, "color": "#dc2626"},
    "cabinet":       {"label": "Cabinet Comptable",   "level": 3, "color": "#2563eb"},
    "collaborateur": {"label": "Collaborateur",       "level": 2, "color": "#7c3aed"},
    "client":        {"label": "Client Final",        "level": 1, "color": "#059669"},
    "demo":          {"label": "Demonstration",       "level": 0, "color": "#d97706"},
}

# --- Plans ---
PLANS = {
    "free":       {"label": "Gratuit",     "quota": 10,  "color": "#6b7280"},
    "starter":    {"label": "Starter",     "quota": 50,  "color": "#0891b2"},
    "pro":        {"label": "Pro",         "quota": 200, "color": "#7c3aed"},
    "enterprise": {"label": "Entreprise",  "quota": -1,  "color": "#d97706"},
}

# --- Permissions par role ---
PERMISSIONS = {
    "admin": ["*"],
    "cabinet": [
        "analyse_facture", "audit_balance", "benford", "alertes", "coherence",
        "compte_resultat", "bilan", "fec", "tva", "immobilisations",
        "tft", "plan_financement", "comparatif", "rapport_client",
        "veille_fiscale", "rapprochement", "balance_agee", "tresorerie",
        "gestion_collaborateurs", "gestion_clients",
    ],
    "collaborateur": [
        "analyse_facture", "audit_balance", "benford", "alertes", "coherence",
        "compte_resultat", "bilan", "fec", "tva", "immobilisations",
        "tft", "plan_financement", "comparatif", "rapport_client",
        "veille_fiscale", "rapprochement", "balance_agee", "tresorerie",
    ],
    "client": [
        "rapport_client", "veille_fiscale",
    ],
    "demo": [
        "analyse_facture", "audit_balance", "benford",
        "compte_resultat", "bilan", "veille_fiscale",
    ],
}


# --- Connexion ---

def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_rbac_db():
    """Initialise/migre les tables RBAC (idempotent)."""
    conn = _conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS smd_users (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            email                   TEXT UNIQUE NOT NULL,
            password_hash           TEXT NOT NULL,
            nom                     TEXT DEFAULT '',
            cabinet                 TEXT DEFAULT '',
            pays                    TEXT DEFAULT 'FR',
            role                    TEXT DEFAULT 'client',
            plan                    TEXT DEFAULT 'free',
            is_active               INTEGER DEFAULT 1,
            quota_used_month        INTEGER DEFAULT 0,
            quota_month             TEXT DEFAULT '',
            stripe_customer_id      TEXT DEFAULT '',
            stripe_subscription_id  TEXT DEFAULT '',
            created_at              TEXT,
            last_login              TEXT
        )
    """)

    migrations = [
        "ALTER TABLE smd_users ADD COLUMN plan TEXT DEFAULT 'free'",
        "ALTER TABLE smd_users ADD COLUMN quota_used_month INTEGER DEFAULT 0",
        "ALTER TABLE smd_users ADD COLUMN quota_month TEXT DEFAULT ''",
        "ALTER TABLE smd_users ADD COLUMN stripe_customer_id TEXT DEFAULT ''",
        "ALTER TABLE smd_users ADD COLUMN stripe_subscription_id TEXT DEFAULT ''",
        "ALTER TABLE smd_users ADD COLUMN last_login TEXT",
    ]
    for m in migrations:
        try:
            c.execute(m)
        except Exception:
            pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS smd_cabinets (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nom         TEXT NOT NULL,
            siret       TEXT DEFAULT '',
            pays        TEXT DEFAULT 'FR',
            plan        TEXT DEFAULT 'starter',
            email_admin TEXT DEFAULT '',
            is_active   INTEGER DEFAULT 1,
            created_at  TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS smd_audit_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email  TEXT,
            action      TEXT NOT NULL,
            resource    TEXT DEFAULT '',
            details     TEXT DEFAULT '',
            app         TEXT DEFAULT '',
            timestamp   TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS smd_quota_usage (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email  TEXT,
            action_type TEXT,
            details     TEXT DEFAULT '',
            month_year  TEXT,
            timestamp   TEXT
        )
    """)

    conn.commit()
    conn.close()


# --- CRUD Utilisateurs ---

def get_user(email):
    """Retourne le user RBAC ou None."""
    email = email.lower().strip()
    init_rbac_db()
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT * FROM smd_users WHERE email=? AND is_active=1", (email,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def creer_user_rbac(email, password, nom="", cabinet="",
                    pays="FR", role="client", plan="free"):
    """Cree un utilisateur RBAC. Retourne {"ok": True} ou {"error": "..."}."""
    email = email.lower().strip()
    if get_user(email):
        return {"error": "Cet email est deja enregistre."}
    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = _conn()
    try:
        conn.execute("""
            INSERT INTO smd_users
              (email, password_hash, nom, cabinet, pays, role, plan, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
        """, (email, pw_hash, nom, cabinet, pays, role, plan, now))
        conn.commit()
        return {"ok": True}
    except sqlite3.IntegrityError:
        return {"error": "Cet email est deja enregistre."}
    finally:
        conn.close()


def verifier_login(email, password):
    """Verifie email + mot de passe RBAC. Retourne user dict ou None."""
    user = get_user(email)
    if not user:
        return None
    try:
        ok = bcrypt.checkpw(
            password.encode("utf-8"),
            user["password_hash"].encode("utf-8")
        )
    except Exception:
        return None
    if ok:
        conn = _conn()
        conn.execute(
            "UPDATE smd_users SET last_login=? WHERE email=?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user["email"])
        )
        conn.commit()
        conn.close()
        return user
    return None


def mettre_a_jour_plan(email, plan):
    """Change le plan d'un utilisateur."""
    if plan not in PLANS:
        return False
    conn = _conn()
    try:
        conn.execute("UPDATE smd_users SET plan=? WHERE email=?",
                     (plan, email.lower().strip()))
        conn.commit()
        return True
    finally:
        conn.close()


def mettre_a_jour_stripe(email, customer_id, subscription_id):
    """Enregistre les IDs Stripe sur le compte."""
    conn = _conn()
    try:
        conn.execute(
            "UPDATE smd_users SET stripe_customer_id=?, stripe_subscription_id=? WHERE email=?",
            (customer_id, subscription_id, email.lower().strip())
        )
        conn.commit()
        return True
    finally:
        conn.close()


def lister_users(role=None, cabinet=None):
    """Liste les utilisateurs. Filtres optionnels."""
    init_rbac_db()
    conn = _conn()
    try:
        if role and cabinet:
            rows = conn.execute(
                "SELECT * FROM smd_users WHERE role=? AND cabinet=? ORDER BY created_at DESC",
                (role, cabinet)
            ).fetchall()
        elif role:
            rows = conn.execute(
                "SELECT * FROM smd_users WHERE role=? ORDER BY created_at DESC", (role,)
            ).fetchall()
        elif cabinet:
            rows = conn.execute(
                "SELECT * FROM smd_users WHERE cabinet=? ORDER BY created_at DESC", (cabinet,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM smd_users ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# --- Quotas ---

def get_quota_limit(user):
    """Retourne la limite mensuelle du plan (-1 = illimite)."""
    plan = user.get("plan", "free")
    return PLANS.get(plan, PLANS["free"])["quota"]


def get_quota_used(user_email):
    """Retourne le nombre d'analyses utilisees ce mois-ci."""
    month = datetime.now().strftime("%Y-%m")
    init_rbac_db()
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT quota_used_month, quota_month FROM smd_users WHERE email=?",
            (user_email.lower().strip(),)
        ).fetchone()
        if row and row["quota_month"] == month:
            return row["quota_used_month"] or 0
        return 0
    finally:
        conn.close()


def incrementer_quota(user_email, action_type="analyse", details=""):
    """
    Incremente le compteur d'analyses.
    Retourne True si OK, False si quota depasse.
    """
    email = user_email.lower().strip()
    user = get_user(email)
    if not user:
        return True
    limit = get_quota_limit(user)
    if limit == -1:
        return True
    month = datetime.now().strftime("%Y-%m")
    used = get_quota_used(email)
    if used >= limit:
        return False

    conn = _conn()
    try:
        if user.get("quota_month") != month:
            conn.execute(
                "UPDATE smd_users SET quota_used_month=1, quota_month=? WHERE email=?",
                (month, email)
            )
        else:
            conn.execute(
                "UPDATE smd_users SET quota_used_month=quota_used_month+1 WHERE email=?",
                (email,)
            )
        conn.execute("""
            INSERT INTO smd_quota_usage (user_email, action_type, details, month_year, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (email, action_type, details, month,
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    finally:
        conn.close()
    return True


# --- Audit logs ---

def log_action(user_email, action, resource="", details="", app=""):
    """Enregistre une action dans les audit logs."""
    init_rbac_db()
    conn = _conn()
    try:
        conn.execute("""
            INSERT INTO smd_audit_logs (user_email, action, resource, details, app, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_email, action, resource, details, app,
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    finally:
        conn.close()


def get_audit_logs(user_email=None, limit=100):
    """Retourne les derniers audit logs."""
    init_rbac_db()
    conn = _conn()
    try:
        if user_email:
            rows = conn.execute(
                "SELECT * FROM smd_audit_logs WHERE user_email=? ORDER BY timestamp DESC LIMIT ?",
                (user_email, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM smd_audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# --- Permissions ---

def has_permission(role, permission):
    """Verifie si un role possede une permission."""
    perms = PERMISSIONS.get(role, [])
    return "*" in perms or permission in perms


def get_role_label(role):
    return ROLES.get(role, {}).get("label", role.capitalize())


def get_plan_label(plan):
    return PLANS.get(plan, {}).get("label", plan.capitalize())
