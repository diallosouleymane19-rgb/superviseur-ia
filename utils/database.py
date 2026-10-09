# -*- coding: utf-8 -*-
"""
utils/database.py - SMD Global Consulting LLC
Gestion clients + analyses (RGPD).
Backend : Supabase PostgreSQL — remplace SQLite.
API identique a l'ancienne version — drop-in replacement.
"""

import logging
from datetime import datetime, timedelta

from utils.db_supabase import get_supabase

logger = logging.getLogger(__name__)

RETENTION_JOURS = 30            # analyses sauvegardées (politique de confidentialité, art. 4)
RETENTION_COMPTE_JOURS = 3 * 365  # compte gratuit inactif : 3 ans après la dernière connexion
RETENTION_JOURNAL_JOURS = 365     # journal des actions et décompte des quotas : 12 mois


# =============================================================================
# Compatibilite — init_db() no-op (schema gere par migrations Supabase)
# =============================================================================
def init_db():
    pass


def _get_current_tenant():
    """Cabinet de l'utilisateur connecté (None : compte sans cabinet, ex. mode démonstration)."""
    try:
        import streamlit as st
        return st.session_state.get("tenant_id") or None
    except Exception:
        return None


def _portee(q):
    """Limite une requête aux données du cabinet connecté (à défaut : de l'utilisateur connecté)."""
    tid = _get_current_tenant()
    return q.eq("tenant_id", str(tid)) if tid else q.eq("user_email", _get_current_user_email())


# =============================================================================
# CLIENTS
# =============================================================================

def creer_client(nom: str, siret: str = "", secteur: str = "",
                 contact: str = "", email: str = "") -> bool:
    try:
        user_email = _get_current_user_email()
        get_supabase().table("clients").insert({
            "nom":        nom,
            "siret":      siret,
            "secteur":    secteur,
            "contact":    contact,
            "email":      email,
            "user_email": user_email,
            "tenant_id":  _get_current_tenant(),
        }).execute()
        _log_action("CREATION_CLIENT", user_email, f"Client : {nom}")
        return True
    except Exception as e:
        logger.error("creer_client : " + str(e))
        return False


def lister_clients() -> list:
    try:
        user_email = _get_current_user_email()
        res = _portee(
            get_supabase()
            .table("clients")
            .select("id, nom, siret, secteur, contact, email, user_email, created_at")
        ).order("nom").execute()
        # Convertit en tuples pour compatibilite ascendante
        rows = []
        for r in (res.data or []):
            rows.append((
                r["id"], r["nom"], r.get("siret", ""),
                r.get("secteur", ""), r.get("contact", ""),
                r.get("email", ""),
                r.get("created_at", "")[:16] if r.get("created_at") else "",
            ))
        return rows
    except Exception as e:
        logger.error("lister_clients : " + str(e))
        return []


def get_client(client_id) -> tuple | None:
    try:
        res = _portee(
            get_supabase()
            .table("clients")
            .select("*")
            .eq("id", int(client_id))
        ).limit(1).execute()
        if res.data:
            r = res.data[0]
            return (
                r["id"], r["nom"], r.get("siret", ""),
                r.get("secteur", ""), r.get("contact", ""),
                r.get("email", ""),
                r.get("created_at", ""),
            )
        return None
    except Exception as e:
        logger.error("get_client : " + str(e))
        return None


def supprimer_client(client_id) -> bool:
    try:
        sb = get_supabase()
        if not get_client(client_id):   # dossier d'un autre cabinet ou inexistant
            return False
        _portee(sb.table("analyses").update({"client_id": None}).eq("client_id", int(client_id))).execute()
        _portee(sb.table("clients").delete().eq("id", int(client_id))).execute()
        _log_action("SUPPRESSION_CLIENT", _get_current_user_email(), f"ID : {client_id}")
        return True
    except Exception as e:
        logger.error("supprimer_client : " + str(e))
        return False


# =============================================================================
# ANALYSES
# =============================================================================

def sauvegarder_analyse(type_analyse=None, resultat=None, client_id=0,
                         titre=None, contenu=None, exercice="", **kwargs) -> bool:
    if contenu is None and resultat is not None:
        contenu = str(resultat)
    elif contenu is None:
        contenu = ""
    if titre is None:
        titre = type_analyse or "Analyse"
    if client_id is None:
        client_id = 0

    expires_at = (datetime.utcnow() + timedelta(days=RETENTION_JOURS)).isoformat()
    user_email = _get_current_user_email()

    try:
        get_supabase().table("analyses").insert({
            "client_id":    int(client_id) if client_id else None,
            "type_analyse": type_analyse,
            "titre":        titre,
            "contenu":      str(contenu),
            "exercice":     exercice,
            "user_email":   user_email,
            "tenant_id":    _get_current_tenant(),
            "expires_at":   expires_at,
        }).execute()
        _log_action("SAUVEGARDE_ANALYSE", user_email, f"Type : {type_analyse}")
        return True
    except Exception as e:
        logger.error("sauvegarder_analyse : " + str(e))
        return False


def lister_analyses(client_id=None) -> list:
    try:
        user_email = _get_current_user_email()
        sb = get_supabase()
        q = _portee(
            sb.table("analyses")
            .select("id, type_analyse, titre, created_at, exercice, user_email")
        )
        if client_id is not None:
            q = q.eq("client_id", int(client_id))
        res = q.order("created_at", desc=True).execute()
        rows = []
        for r in (res.data or []):
            rows.append((
                r["id"],
                r.get("type_analyse", ""),
                r.get("titre", ""),
                r.get("created_at", "")[:16] if r.get("created_at") else "",
                r.get("exercice", ""),
            ))
        return rows
    except Exception as e:
        logger.error("lister_analyses : " + str(e))
        return []


def get_analyse(analyse_id) -> tuple | None:
    try:
        res = _portee(
            get_supabase()
            .table("analyses")
            .select("*")
            .eq("id", int(analyse_id))
        ).limit(1).execute()
        if res.data:
            r = res.data[0]
            return (
                r["id"],
                r.get("client_id"),
                r.get("type_analyse", ""),
                r.get("titre", ""),
                r.get("contenu", ""),
                r.get("created_at", ""),
                r.get("expires_at", ""),
                r.get("exercice", ""),
                r.get("user_email", ""),
            )
        return None
    except Exception as e:
        logger.error("get_analyse : " + str(e))
        return None


def supprimer_analyse(analyse_id) -> bool:
    try:
        if not get_analyse(analyse_id):   # analyse d'un autre cabinet ou inexistante
            return False
        _portee(get_supabase().table("analyses").delete().eq("id", int(analyse_id))).execute()
        _log_action("SUPPRESSION_ANALYSE", _get_current_user_email(), f"ID : {analyse_id}")
        return True
    except Exception as e:
        logger.error("supprimer_analyse : " + str(e))
        return False


_DERNIERE_PURGE = 0.0


def purger_si_necessaire(intervalle_s: int = 3600) -> bool:
    """Lance la purge RGPD au plus une fois par heure et par serveur (appelée à chaque chargement de page).
    Retourne True si une purge a été lancée."""
    global _DERNIERE_PURGE
    import time
    from utils.db_supabase import supabase_disponible
    if time.time() - _DERNIERE_PURGE < intervalle_s or not supabase_disponible():
        return False
    _DERNIERE_PURGE = time.time()
    purger_donnees_expirees()
    purger_journaux()
    purger_comptes_inactifs()
    return True


def purger_journaux():
    """Supprime le journal des actions et le décompte des quotas de plus de 12 mois (RGPD)."""
    limite = (datetime.utcnow() - timedelta(days=RETENTION_JOURNAL_JOURS)).isoformat()
    for table in ("audit_logs", "smd_quota_usage"):
        try:
            res = get_supabase().table(table).delete().lt("created_at", limite).execute()
            if res.data:
                logger.info(f"RGPD : {len(res.data)} ligne(s) supprimée(s) dans {table}")
        except Exception as e:
            logger.error(f"purger_journaux {table} : {e}")


def purger_comptes_inactifs() -> int:
    """Supprime les comptes sans connexion depuis 3 ans (jamais connectés : depuis la création) dont le cabinet
    est au plan gratuit, avec leurs données liées. Un cabinet qui n'a plus aucun membre est supprimé avec ses
    dossiers, analyses et invitations. Les abonnements payants (relation en cours) et les administrateurs ne sont
    jamais supprimés. Retourne le nombre de comptes supprimés."""
    limite = (datetime.utcnow() - timedelta(days=RETENTION_COMPTE_JOURS)).isoformat()
    try:
        sb = get_supabase()
        res = (sb.table("users").select("id, email, plan, tenant_id")
               .neq("role", "admin")
               .or_(f"last_login.lt.{limite},and(last_login.is.null,created_at.lt.{limite})")
               .execute())
        supprimes = 0
        for c in res.data or []:
            cab = None
            if c.get("tenant_id"):
                r = sb.table("smd_cabinets").select("id, plan").eq("id", str(c["tenant_id"])).limit(1).execute()
                cab = r.data[0] if r.data else None
            if (cab.get("plan") if cab else c.get("plan")) not in (None, "", "free"):
                continue   # abonnement payant en cours : jamais supprimé
            sb.table("audit_logs").delete().eq("user_id", c["id"]).execute()
            sb.table("smd_quota_usage").delete().eq("user_email", c["email"]).execute()
            for table in ("analyses", "clients"):   # données hors cabinet
                sb.table(table).delete().eq("user_email", c["email"]).is_("tenant_id", "null").execute()
            sb.table("users").delete().eq("id", c["id"]).execute()   # chat_sessions : suppression en cascade
            supprimes += 1
            if cab:
                reste = sb.table("users").select("id", count="exact").eq("tenant_id", str(cab["id"])).execute().count
                if not reste:   # cabinet vide : supprimé avec ses dossiers, analyses et invitations (cascade)
                    sb.table("smd_cabinets").delete().eq("id", str(cab["id"])).execute()
        if supprimes:
            _log_action("PURGE_COMPTES_INACTIFS", "system", f"{supprimes} compte(s) gratuit(s) inactif(s) depuis 3 ans")
        return supprimes
    except Exception as e:
        logger.error("purger_comptes_inactifs : " + str(e))
        return 0


def purger_donnees_expirees():
    """Supprime les analyses dont expires_at est depasse (RGPD)."""
    try:
        now = datetime.utcnow().isoformat()
        res = (
            get_supabase()
            .table("analyses")
            .delete()
            .lt("expires_at", now)
            .execute()
        )
        nb = len(res.data or [])
        if nb > 0:
            logger.info(f"RGPD : {nb} analyse(s) expiree(s) supprimee(s)")
    except Exception as e:
        logger.error("purger_donnees_expirees : " + str(e))


# =============================================================================
# Helpers
# =============================================================================

def _get_current_user_email() -> str:
    try:
        import streamlit as st
        return st.session_state.get("user_email", "system")
    except Exception:
        return "system"


def _log_action(action: str, user_email: str = "", detail: str = ""):
    try:
        get_supabase().table("audit_logs").insert({
            "action":  action,
            "module":  "database",
            "details": {"user_email": user_email, "detail": detail},
        }).execute()
    except Exception:
        pass
