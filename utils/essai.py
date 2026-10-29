# -*- coding: utf-8 -*-
"""
utils/essai.py - SMD Global Consulting LLC
Essai Pro « Dossier Propre en 14 jours », sans carte bancaire, porté par le cabinet :
- démarré automatiquement à l'inscription d'un nouveau cabinet, ou depuis la page Abonnement
  par un cabinet au plan Gratuit qui ne l'a jamais utilisé (un seul essai par cabinet) ;
- le cabinet passe au plan Pro jusqu'à la date de fin (colonne smd_cabinets.essai_fin) ;
- à la date de fin, sans abonnement Stripe, retour automatique au plan Gratuit (à la lecture du compte
  et par la tâche horaire) ; un e-mail de rappel part 3 jours avant la fin quand l'envoi est possible.
Un abonnement Stripe souscrit pendant l'essai prend le relais : l'essai n'est alors plus jamais expiré.
"""
import logging
import math
from datetime import datetime, timedelta, timezone

from utils.db_supabase import get_supabase

logger = logging.getLogger("superviseur_ia")

ESSAI_JOURS = 14
RAPPEL_JOURS = 3
PLAN_ESSAI = "pro"
NOM_ESSAI = "Dossier Propre en 14 jours"

_COLONNES_PRETES = False


def _maintenant():
    return datetime.now(timezone.utc)


def assurer_colonnes() -> bool:
    """Ajoute smd_cabinets.essai_fin et essai_rappel si elles manquent (base OVH). Sans effet sur les données."""
    global _COLONNES_PRETES
    if _COLONNES_PRETES:
        return True
    try:
        from utils.db_supabase import _database_url
        if not _database_url():
            return False
        from psycopg import sql
        sb = get_supabase()
        sb._lire(sql.SQL("ALTER TABLE smd_cabinets ADD COLUMN IF NOT EXISTS essai_fin timestamptz"), [])
        sb._lire(sql.SQL("ALTER TABLE smd_cabinets ADD COLUMN IF NOT EXISTS essai_rappel boolean DEFAULT false"), [])
        getattr(sb, "_cache_types", {}).pop("smd_cabinets", None)
        _COLONNES_PRETES = True
        return True
    except Exception as e:
        logger.error(f"essai.assurer_colonnes : {e}")
        return False


def _date(v):
    """essai_fin lu en base : datetime ou texte ISO -> datetime avec fuseau (None si absent)."""
    if not v:
        return None
    if isinstance(v, str):
        try:
            v = datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None
    return v if v.tzinfo else v.replace(tzinfo=timezone.utc)


def _abonne(cab: dict) -> bool:
    return bool((cab or {}).get("stripe_subscription_id"))


def jours_restants(cab: dict):
    """Jours restants d'un essai en cours (au moins 1 le dernier jour), None s'il n'y a pas d'essai en cours."""
    fin = _date((cab or {}).get("essai_fin"))
    if not fin or (cab or {}).get("plan") != PLAN_ESSAI or _abonne(cab) or fin <= _maintenant():
        return None
    return max(1, math.ceil((fin - _maintenant()).total_seconds() / 86400))


def essai_possible(cab: dict) -> bool:
    """Un cabinet au plan Gratuit qui n'a jamais eu d'essai peut en démarrer un."""
    return bool(cab) and (cab.get("plan") or "free") == "free" and not cab.get("essai_fin") and not _abonne(cab)


def _appliquer_plan(tenant_id, plan: str, extra: dict | None = None):
    sb = get_supabase()
    sb.table("smd_cabinets").update({"plan": plan, "updated_at": _maintenant().isoformat(), **(extra or {})}) \
        .eq("id", str(tenant_id)).execute()
    sb.table("users").update({"plan": plan, "updated_at": _maintenant().isoformat()}) \
        .eq("tenant_id", str(tenant_id)).execute()


def demarrer_essai(tenant_id, email: str = "") -> bool:
    """Passe le cabinet au plan Pro pour 14 jours. False si l'essai n'est pas possible."""
    if not tenant_id or not assurer_colonnes():
        return False
    from utils.cabinets import get_cabinet
    cab = get_cabinet(tenant_id)
    if not essai_possible(cab):
        return False
    fin = _maintenant() + timedelta(days=ESSAI_JOURS)
    try:
        _appliquer_plan(tenant_id, PLAN_ESSAI, {"essai_fin": fin.isoformat(), "essai_rappel": False})
        from utils.auth_rbac import log_action
        log_action(email or cab.get("email_admin", ""), "ESSAI_DEBUT",
                   details=f"Essai Pro « {NOM_ESSAI} » jusqu'au {fin.astimezone().strftime('%d/%m/%Y')}")
        return True
    except Exception as e:
        logger.error(f"demarrer_essai : {e}")
        return False


def expirer_si_termine(cab: dict) -> dict:
    """Essai terminé sans abonnement : retour au plan Gratuit. Retourne le cabinet à jour."""
    fin = _date((cab or {}).get("essai_fin"))
    if not fin or cab.get("plan") != PLAN_ESSAI or _abonne(cab) or fin > _maintenant():
        return cab
    try:
        _appliquer_plan(cab["id"], "free")
        from utils.auth_rbac import log_action
        log_action(cab.get("email_admin", "") or "system", "ESSAI_FIN",
                   details=f"Fin de l'essai Pro « {NOM_ESSAI} » : retour au plan Gratuit")
        return {**cab, "plan": "free"}
    except Exception as e:
        logger.error(f"expirer_si_termine : {e}")
        return cab


def _texte_rappel(cab: dict, fin: datetime) -> str:
    return (f"Bonjour,\n\n"
            f"L'essai Pro « {NOM_ESSAI} » du cabinet {cab.get('nom', '')} se termine le "
            f"{fin.astimezone().strftime('%d/%m/%Y')}.\n\n"
            "Après cette date, le cabinet repassera au plan Gratuit (10 analyses par mois) : vos analyses "
            "sauvegardées et vos dossiers clients restent accessibles.\n\n"
            "Pour garder tous les modules et 200 analyses par mois, choisissez un plan dans KontrolIA, "
            "rubrique Abonnement : https://app.smdconsulting.pro\n\n"
            "Une question ? Répondez simplement à cet e-mail.\n\n"
            "KontrolIA - SMD Global Consulting LLC")


def taches_essais() -> dict:
    """Tâche horaire : fin des essais échus et rappel 3 jours avant la fin. Retourne les compteurs."""
    stats = {"expires": 0, "rappels": 0}
    if not assurer_colonnes():
        return stats
    try:
        res = get_supabase().table("smd_cabinets").select("*").eq("plan", PLAN_ESSAI).execute()
    except Exception as e:
        logger.error(f"taches_essais : {e}")
        return stats
    envoi = None
    for cab in res.data or []:
        fin = _date(cab.get("essai_fin"))
        if not fin or _abonne(cab):
            continue
        if fin <= _maintenant():
            if expirer_si_termine(cab).get("plan") == "free":
                stats["expires"] += 1
        elif fin - _maintenant() <= timedelta(days=RAPPEL_JOURS) and not cab.get("essai_rappel") and cab.get("email_admin"):
            from utils.email_envoi import envoi_possible, envoyer_email
            if envoi is None:
                envoi = envoi_possible()
            if envoi and envoyer_email(cab["email_admin"], f"Votre essai KontrolIA se termine le "
                                       f"{fin.astimezone().strftime('%d/%m/%Y')}", _texte_rappel(cab, fin)):
                get_supabase().table("smd_cabinets").update({"essai_rappel": True}).eq("id", str(cab["id"])).execute()
                stats["rappels"] += 1
    return stats
