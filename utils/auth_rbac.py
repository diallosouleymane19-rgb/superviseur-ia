# -*- coding: utf-8 -*-
"""
utils/auth_rbac.py - SMD Global Consulting LLC
Module RBAC : rôles, plans, quotas, journal des actions.
Backend : Supabase PostgreSQL (remplace SQLite /tmp/smd_users.db).
API identique à l'ancienne version — drop-in replacement.
"""

import bcrypt
from datetime import datetime

from utils.db_supabase import get_supabase

# --- Roles ---
ROLES = {
    "admin":         {"label": "Administrateur SMD",  "level": 4, "color": "#dc2626"},
    "cabinet":       {"label": "Responsable du cabinet", "level": 3, "color": "#2563eb"},
    "collaborateur": {"label": "Collaborateur",       "level": 2, "color": "#7c3aed"},
    "client":        {"label": "Client Final",        "level": 1, "color": "#059669"},
    "demo":          {"label": "Démonstration",       "level": 0, "color": "#d97706"},
}

# --- Plans ---
PLANS = {
    "free":       {"label": "Gratuit",    "quota": 10,  "color": "#6b7280"},
    "starter":    {"label": "Starter",    "quota": 50,  "color": "#0891b2"},
    "pro":        {"label": "Pro",        "quota": 200, "color": "#7c3aed"},
    "enterprise": {"label": "Entreprise", "quota": -1,  "color": "#d97706"},
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
    "client": ["rapport_client", "veille_fiscale"],
    "demo":   ["analyse_facture", "audit_balance", "benford",
               "compte_resultat", "bilan", "veille_fiscale"],
}


# =============================================================================
# Compatibilite — init_rbac_db() no-op (schema gere par migrations Supabase)
# =============================================================================
def init_rbac_db():
    pass


# =============================================================================
# CRUD Utilisateurs
# =============================================================================

def get_user(email: str):
    """Retourne le user dict (avec le plan, l'abonnement et le quota de son cabinet) ou None."""
    try:
        email = email.lower().strip()
        sb = get_supabase()
        res = (
            sb.table("users")
            .select("*")
            .eq("email", email)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        from utils.cabinets import enrichir_user
        return enrichir_user(res.data[0]) if res.data else None
    except Exception as e:
        _log_error("get_user", str(e))
        return None


def creer_user_rbac(email: str, password: str, nom: str = "",
                    cabinet: str = "", pays: str = "FR",
                    role: str = "client", plan: str = "free") -> dict:
    """Crée un utilisateur. Retourne {'ok': True, ...} ou {'error': '...'}.
    Invitation en attente pour cet e-mail : le compte rejoint le cabinet qui l'a invité (collaborateur).
    Sinon : un nouveau cabinet est créé et l'utilisateur en est le responsable."""
    email = email.lower().strip()
    if get_user(email):
        return {"error": "Cet email est déjà enregistre."}
    from utils.cabinets import invitation_pour, creer_cabinet, marquer_acceptee, get_cabinet, ROLE_COLLABORATEUR
    invitation = invitation_pour(email)
    try:
        if invitation:
            tenant_id = invitation["tenant_id"]
            role = ROLE_COLLABORATEUR
            cab = get_cabinet(tenant_id) or {}
            cabinet, plan = cab.get("nom", cabinet), cab.get("plan", "free")
        else:
            tenant_id = creer_cabinet(cabinet, email, pays, plan)
    except Exception as e:
        _log_error("creer_user_rbac/cabinet", str(e))
        return {"error": "Erreur création du cabinet : " + str(e)[:80]}

    pw_hash = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    try:
        get_supabase().table("users").insert({
            "email":                  email,
            "password_hash":          pw_hash,
            "nom":                    nom,
            "full_name":              nom,
            "cabinet":                cabinet,
            "company":                cabinet,
            "pays":                   pays,
            "role":                   role,
            "plan":                   plan,
            "is_active":              True,
            "quota_used_month":       0,
            "quota_month":            "",
            "stripe_customer_id":     "",
            "stripe_subscription_id": "",
            "tenant_id":              tenant_id,
        }).execute()
        if invitation:
            marquer_acceptee(invitation["id"])
        return {"ok": True, "tenant_id": tenant_id, "invite": bool(invitation),
                "cabinet": cabinet}
    except Exception as e:
        msg = str(e)
        if not invitation and tenant_id:   # cabinet créé pour rien : supprimé
            try:
                get_supabase().table("smd_cabinets").delete().eq("id", str(tenant_id)).execute()
            except Exception:
                pass
        if "unique" in msg.lower() or "duplicate" in msg.lower():
            return {"error": "Cet email est déjà enregistre."}
        _log_error("creer_user_rbac", msg)
        return {"error": "Erreur création compte : " + msg[:80]}


def verifier_login(email: str, password: str):
    """Vérifie email + mot de passe. Retourne user dict ou None."""
    user = get_user(email)
    if not user:
        return None
    pw_hash = user.get("password_hash", "")
    if not pw_hash:
        return None
    try:
        ok = bcrypt.checkpw(password.encode("utf-8"), pw_hash.encode("utf-8"))
    except Exception:
        return None
    if ok:
        _update_last_login(email)
        return user
    return None


def _update_last_login(email: str):
    try:
        get_supabase().table("users").update({
            "last_login": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("email", email).execute()
    except Exception:
        pass


def mettre_a_jour_plan(email: str, plan: str) -> bool:
    """Plan de l'abonnement : porté par le cabinet de l'utilisateur (et recopié sur le compte)."""
    if plan not in PLANS:
        return False
    try:
        user = get_user(email)
        if user and user.get("tenant_id"):
            from utils.cabinets import mettre_a_jour_cabinet
            mettre_a_jour_cabinet(user["tenant_id"], {"plan": plan})
        get_supabase().table("users").update({
            "plan":       plan,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("email", email.lower().strip()).execute()
        return True
    except Exception as e:
        _log_error("mettre_a_jour_plan", str(e))
        return False


def mettre_a_jour_stripe(email: str, customer_id: str,
                          subscription_id: str) -> bool:
    """Client et abonnement Stripe : portés par le cabinet de l'utilisateur."""
    try:
        user = get_user(email)
        if user and user.get("tenant_id"):
            from utils.cabinets import mettre_a_jour_cabinet
            mettre_a_jour_cabinet(user["tenant_id"], {"stripe_customer_id": customer_id,
                                                      "stripe_subscription_id": subscription_id})
        get_supabase().table("users").update({
            "stripe_customer_id":     customer_id,
            "stripe_subscription_id": subscription_id,
            "updated_at":             datetime.utcnow().isoformat(),
        }).eq("email", email.lower().strip()).execute()
        return True
    except Exception as e:
        _log_error("mettre_a_jour_stripe", str(e))
        return False


def lister_users(role: str = None, cabinet: str = None) -> list:
    try:
        sb = get_supabase()
        q = sb.table("users").select("*")
        if role:
            q = q.eq("role", role)
        if cabinet:
            q = q.eq("cabinet", cabinet)
        res = q.order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        _log_error("lister_users", str(e))
        return []


# =============================================================================
# Quotas
# =============================================================================

def get_quota_limit(user: dict) -> int:
    plan = user.get("plan", "free")
    return PLANS.get(plan, PLANS["free"])["quota"]


def get_quota_used(user_email: str) -> int:
    """Analyses consommées ce mois : par le cabinet entier (quota partagé)."""
    month = datetime.now().strftime("%Y-%m")
    user = get_user(user_email)
    if user and user.get("tenant_id"):
        return (user.get("quota_used_month") or 0) if user.get("quota_month") == month else 0
    try:
        res = (
            get_supabase()
            .table("users")
            .select("quota_used_month, quota_month")
            .eq("email", user_email.lower().strip())
            .limit(1)
            .execute()
        )
        if res.data:
            row = res.data[0]
            if row.get("quota_month") == month:
                return row.get("quota_used_month") or 0
        return 0
    except Exception:
        return 0


def incrementer_quota(user_email: str, action_type: str = "analyse",
                      details: str = "") -> bool:
    """Incrémente le compteur. Retourne False si quota dépassé."""
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

    try:
        sb = get_supabase()
        if user.get("quota_month") != month:
            new_used = 1
        else:
            new_used = (user.get("quota_used_month") or 0) + 1

        if user.get("tenant_id"):   # quota partagé par le cabinet
            from utils.cabinets import mettre_a_jour_cabinet
            mettre_a_jour_cabinet(user["tenant_id"], {"quota_used_month": new_used, "quota_month": month})
        else:
            sb.table("users").update({
                "quota_used_month": new_used,
                "quota_month":      month,
                "updated_at":       datetime.utcnow().isoformat(),
            }).eq("email", email).execute()

        sb.table("smd_quota_usage").insert({
            "user_email":  email,
            "action_type": action_type,
            "details":     details,
            "month_year":  month,
        }).execute()
    except Exception as e:
        _log_error("incrementer_quota", str(e))

    return True


# =============================================================================
# Audit logs
# =============================================================================

def log_action(user_email: str, action: str, resource: str = "",
               details: str = "", app: str = ""):
    try:
        get_supabase().table("audit_logs").insert({
            "action": action,
            "module": resource or app or None,
            "details": {
                "user_email": user_email,
                "resource":   resource,
                "details":    details,
                "app":        app,
            },
        }).execute()
    except Exception:
        pass


def get_audit_logs(user_email: str = None, limit: int = 100) -> list:
    try:
        sb = get_supabase()
        q = sb.table("audit_logs").select("*")
        res = q.order("created_at", desc=True).limit(limit).execute()
        rows = res.data or []
        if user_email:
            rows = [
                r for r in rows
                if isinstance(r.get("details"), dict)
                and r["details"].get("user_email") == user_email
            ]
        return rows
    except Exception:
        return []


# =============================================================================
# Permissions
# =============================================================================

def has_permission(role: str, permission: str) -> bool:
    perms = PERMISSIONS.get(role, [])
    return "*" in perms or permission in perms


def get_role_label(role: str) -> str:
    return ROLES.get(role, {}).get("label", role.capitalize())


def get_plan_label(plan: str) -> str:
    return PLANS.get(plan, {}).get("label", plan.capitalize())


def _log_error(fn: str, msg: str):
    try:
        import logging
        logging.getLogger("auth_rbac").error(fn + " : " + msg)
    except Exception:
        pass
