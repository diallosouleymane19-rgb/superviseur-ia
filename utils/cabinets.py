# -*- coding: utf-8 -*-
"""
utils/cabinets.py - SMD Global Consulting LLC
Multi-cabinets : un cabinet (table smd_cabinets) regroupe un responsable et ses collaborateurs.
- Les dossiers clients et les analyses sauvegardées sont partagés dans le cabinet (colonne tenant_id).
- L'abonnement Stripe et le quota mensuel d'analyses sont portés par le cabinet.
- Un collaborateur rejoint un cabinet sur invitation du responsable (table smd_invitations).
"""
import re
from datetime import datetime, timezone

from utils.db_supabase import get_supabase

# Champs de facturation portés par le cabinet (et non plus par l'utilisateur)
CHAMPS_CABINET = ("plan", "stripe_customer_id", "stripe_subscription_id", "quota_used_month", "quota_month", "essai_fin")
ROLE_RESPONSABLE = "cabinet"
ROLE_COLLABORATEUR = "collaborateur"
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _maintenant():
    return datetime.now(timezone.utc).isoformat()


# ─── Cabinet ────────────────────────────────────────────────────────────────

def creer_cabinet(nom: str, email_admin: str, pays: str = "FR", plan: str = "free") -> str | None:
    """Crée un cabinet et retourne son identifiant."""
    res = get_supabase().table("smd_cabinets").insert({
        "nom": (nom or "").strip() or email_admin.split("@")[0],
        "email_admin": email_admin, "pays": pays or "FR", "plan": plan or "free",
        "quota_used_month": 0, "quota_month": "", "stripe_customer_id": "", "stripe_subscription_id": "",
    }).execute()
    return res.data[0]["id"] if res.data else None


def get_cabinet(tenant_id) -> dict | None:
    if not tenant_id:
        return None
    try:
        res = get_supabase().table("smd_cabinets").select("*").eq("id", str(tenant_id)).limit(1).execute()
        return res.data[0] if res.data else None
    except Exception:
        return None


def mettre_a_jour_cabinet(tenant_id, valeurs: dict) -> bool:
    if not tenant_id:
        return False
    try:
        get_supabase().table("smd_cabinets").update({**valeurs, "updated_at": _maintenant()}) \
            .eq("id", str(tenant_id)).execute()
        return True
    except Exception:
        return False


def renommer_cabinet(tenant_id, nom: str) -> bool:
    nom = (nom or "").strip()
    if not nom:
        return False
    ok = mettre_a_jour_cabinet(tenant_id, {"nom": nom})
    if ok:   # le nom affiché des membres suit le cabinet
        try:
            get_supabase().table("users").update({"cabinet": nom, "company": nom}).eq("tenant_id", str(tenant_id)).execute()
        except Exception:
            pass
    return ok


def enrichir_user(user: dict | None) -> dict | None:
    """Ajoute au compte les informations de son cabinet : plan, abonnement, quota, nom du cabinet."""
    if not user:
        return user
    cab = get_cabinet(user.get("tenant_id"))
    if cab and cab.get("essai_fin"):
        from utils.essai import expirer_si_termine
        cab = expirer_si_termine(cab)   # essai Pro échu sans abonnement : retour au plan Gratuit
    if cab:
        u = dict(user)
        for k in CHAMPS_CABINET:
            u[k] = cab.get(k) if cab.get(k) is not None else u.get(k)
        u["cabinet"] = cab.get("nom") or u.get("cabinet", "")
        u["cabinet_nom"] = cab.get("nom", "")
        return u
    return user


# ─── Membres ────────────────────────────────────────────────────────────────

def membres(tenant_id) -> list:
    if not tenant_id:
        return []
    try:
        res = (get_supabase().table("users")
               .select("email, nom, role, is_active, last_login, created_at")
               .eq("tenant_id", str(tenant_id)).eq("is_active", True)
               .order("created_at").execute())
        return res.data or []
    except Exception:
        return []


def retirer_membre(tenant_id, email: str, par: str = "") -> dict:
    """Retire un collaborateur : son compte est fermé (il ne peut plus se connecter).
    Les analyses qu'il a sauvegardées restent dans le cabinet."""
    email = (email or "").lower().strip()
    if email == (par or "").lower().strip():
        return {"error": "Vous ne pouvez pas vous retirer vous-même."}
    m = next((x for x in membres(tenant_id) if x["email"] == email), None)
    if not m:
        return {"error": "Ce membre n'appartient pas à votre cabinet."}
    if m.get("role") != ROLE_COLLABORATEUR:
        return {"error": "Seuls les collaborateurs peuvent être retirés."}
    try:
        # Plan remis à « gratuit » : le compte fermé suit la purge des comptes inactifs (3 ans)
        get_supabase().table("users").update({"is_active": False, "tenant_id": None, "plan": "free",
                                              "stripe_customer_id": "", "stripe_subscription_id": "",
                                              "updated_at": _maintenant()}) \
            .eq("email", email).eq("tenant_id", str(tenant_id)).execute()
        return {"ok": True}
    except Exception as e:
        return {"error": f"Retrait impossible : {str(e)[:80]}"}


# ─── Invitations ────────────────────────────────────────────────────────────

def invitations_en_attente(tenant_id) -> list:
    if not tenant_id:
        return []
    try:
        res = (get_supabase().table("smd_invitations").select("*")
               .eq("tenant_id", str(tenant_id)).is_("accepted_at", "null")
               .order("created_at", desc=True).execute())
        return [i for i in (res.data or []) if not _expiree(i)]
    except Exception:
        return []


def _expiree(inv: dict) -> bool:
    exp = inv.get("expires_at")
    if not exp:
        return False
    try:
        return datetime.fromisoformat(str(exp).replace("Z", "+00:00")) < datetime.now(timezone.utc)
    except ValueError:
        return False


def inviter(tenant_id, email: str, par: str = "") -> dict:
    """Invite un collaborateur. Il crée ensuite son compte avec cet e-mail et rejoint le cabinet."""
    email = (email or "").lower().strip()
    if not _EMAIL.match(email):
        return {"error": "Adresse e-mail invalide."}
    sb = get_supabase()
    try:
        if sb.table("users").select("id").eq("email", email).limit(1).execute().data:
            return {"error": "Un compte existe déjà avec cet e-mail (actif ou fermé) : il ne peut pas rejoindre "
                             "votre cabinet. Contactez contact@smdconsulting.pro si besoin."}
        attente = sb.table("smd_invitations").select("id, tenant_id, expires_at").eq("email", email) \
            .is_("accepted_at", "null").execute().data or []
        for inv in attente:
            if _expiree(inv):   # invitation périmée : on la remplace
                sb.table("smd_invitations").delete().eq("id", inv["id"]).execute()
            elif str(inv["tenant_id"]) == str(tenant_id):
                return {"error": "Une invitation est déjà en attente pour cet e-mail."}
            else:
                return {"error": "Cette personne a déjà une invitation en attente dans un autre cabinet."}
        sb.table("smd_invitations").insert({"tenant_id": str(tenant_id), "email": email,
                                            "role": ROLE_COLLABORATEUR, "invited_by": par}).execute()
        return {"ok": True}
    except Exception as e:
        return {"error": f"Invitation impossible : {str(e)[:80]}"}


def annuler_invitation(tenant_id, invitation_id) -> bool:
    try:
        get_supabase().table("smd_invitations").delete() \
            .eq("id", str(invitation_id)).eq("tenant_id", str(tenant_id)).execute()
        return True
    except Exception:
        return False


def invitation_pour(email: str) -> dict | None:
    """Invitation valide (non acceptée, non expirée) pour cet e-mail, avec le nom du cabinet."""
    email = (email or "").lower().strip()
    try:
        res = get_supabase().table("smd_invitations").select("*").eq("email", email) \
            .is_("accepted_at", "null").execute()
        inv = next((i for i in (res.data or []) if not _expiree(i)), None)
        if inv:
            cab = get_cabinet(inv["tenant_id"])
            if not cab or cab.get("is_active") is False:
                return None
            inv["cabinet_nom"] = cab.get("nom", "")
        return inv
    except Exception:
        return None


def marquer_acceptee(invitation_id) -> None:
    try:
        get_supabase().table("smd_invitations").update({"accepted_at": _maintenant()}) \
            .eq("id", str(invitation_id)).execute()
    except Exception:
        pass


# ─── Indicateurs du cabinet ─────────────────────────────────────────────────

def compter(tenant_id) -> dict:
    """Nombre de membres actifs et d'analyses sauvegardées ce mois, pour ce cabinet seulement."""
    res = {"membres": 0, "analyses": 0}
    if not tenant_id:
        return res
    try:
        sb = get_supabase()
        mois = datetime.now().strftime("%Y-%m")
        res["membres"] = sb.table("users").select("id", count="exact").eq("tenant_id", str(tenant_id)) \
            .eq("is_active", True).execute().count or 0
        res["analyses"] = sb.table("analyses").select("id", count="exact").eq("tenant_id", str(tenant_id)) \
            .gte("created_at", mois + "-01").execute().count or 0
    except Exception:
        pass
    return res


# ─── Suppression d'un compte (administrateur de la plateforme) ──────────────

def _abonnement_actif(cab: dict) -> bool:
    """Abonnement Stripe en cours pour ce cabinet (un client du mode test, inconnu en mode réel, n'en a pas)."""
    if not cab or not cab.get("stripe_customer_id"):
        return False
    try:
        from utils.stripe_billing import _init_stripe, abonnements_actifs
        _init_stripe()
        return bool(abonnements_actifs(cab["stripe_customer_id"]))
    except Exception:
        return False


def supprimer_compte(email: str, par: str = "") -> dict:
    """Supprime définitivement un compte. S'il est le seul membre de son cabinet, le cabinet est supprimé avec
    ses dossiers, analyses et invitations. Refusé pour un administrateur, pour soi-même, et pour un cabinet
    dont l'abonnement Stripe est en cours (à résilier d'abord dans Stripe)."""
    email = (email or "").lower().strip()
    if not email or email == (par or "").lower().strip():
        return {"error": "Vous ne pouvez pas supprimer votre propre compte ici."}
    sb = get_supabase()
    res = sb.table("users").select("id, email, role, tenant_id").eq("email", email).limit(1).execute().data
    if not res:
        return {"error": "Compte introuvable."}
    u = res[0]
    if u.get("role") == "admin":
        return {"error": "Un compte administrateur ne peut pas être supprimé ici."}
    cab = get_cabinet(u.get("tenant_id"))
    seul = bool(cab) and len(sb.table("users").select("id").eq("tenant_id", str(cab["id"])).execute().data or []) == 1
    if seul and _abonnement_actif(cab):
        return {"error": "Ce cabinet a un abonnement Stripe en cours : résiliez-le d'abord dans Stripe."}
    try:
        sb.table("audit_logs").delete().eq("user_id", u["id"]).execute()
        sb.table("smd_quota_usage").delete().eq("user_email", email).execute()
        for table in ("analyses", "clients"):   # données hors cabinet
            sb.table(table).delete().eq("user_email", email).is_("tenant_id", "null").execute()
        if seul:   # dossiers, analyses et invitations du cabinet : suppression en cascade
            sb.table("smd_cabinets").delete().eq("id", str(cab["id"])).execute()
        sb.table("users").delete().eq("id", u["id"]).execute()
    except Exception as e:
        return {"error": f"Suppression impossible : {str(e)[:120]}"}
    from utils.auth_rbac import log_action
    log_action(par or "admin", "SUPPRESSION_COMPTE",
               details=f"{email}" + (f" et son cabinet « {cab.get('nom', '')} »" if seul else ""))
    return {"ok": True, "cabinet_supprime": seul, "cabinet": (cab or {}).get("nom", "")}
