# -*- coding: utf-8 -*-
"""
utils/page_supervision.py - SMD Global Consulting LLC
Supervision de la plateforme KontrolIA (administrateur uniquement) :
qui est en ligne, qui est actif, nouveaux comptes, journal des actions.

« En ligne » = activité (clic, analyse) depuis moins de 15 minutes : l'application ne peut pas savoir
à la seconde près si un onglet est encore ouvert. La dernière activité est notée au plus toutes les 5 minutes.
"""
import time
from datetime import datetime, timedelta, timezone

import streamlit as st

EN_LIGNE_MINUTES = 15
INTERVALLE_ACTIVITE = 300          # secondes entre deux écritures de « dernière activité »
try:
    from zoneinfo import ZoneInfo
    PARIS = ZoneInfo("Europe/Paris")
except Exception:                  # pragma: no cover
    PARIS = timezone.utc

ACTIONS = {
    "login": "Connexion",
    "LOGIN_ECHEC": "Échec de connexion",
    "MDP_DEMANDE": "Demande de nouveau mot de passe",
    "MDP_REINITIALISE": "Mot de passe réinitialisé",
    "INSCRIPTION": "Inscription",
    "ESSAI_DEBUT": "Début de l'essai Pro",
    "ESSAI_FIN": "Fin de l'essai Pro",
    "ABONNEMENT": "Abonnement (paiement Stripe)",
    "ANALYSE": "Analyse lancée",
    "SAUVEGARDE_ANALYSE": "Sauvegarde d'analyse",
    "SUPPRESSION_ANALYSE": "Suppression d'analyse",
    "CREATION_CLIENT": "Création de dossier client",
    "MODIFICATION_CLIENT": "Modification de dossier client",
    "SUPPRESSION_CLIENT": "Suppression de dossier client",
    "PURGE_COMPTES_INACTIFS": "Purge des comptes inactifs",
}


# ─── Colonne « dernière activité » et enregistrement ─────────────────────────

@st.cache_resource(show_spinner=False)
def _colonne_activite_prete() -> bool:
    """Ajoute users.last_seen si elle manque (base OVH). Sans effet sur les données existantes."""
    try:
        from utils.db_supabase import _database_url, get_supabase
        if not _database_url():
            return False
        from psycopg import sql
        sb = get_supabase()
        sb._lire(sql.SQL("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen timestamptz"), [])
        sb._cache_types.pop("users", None)
        return True
    except Exception:
        return False


def noter_activite() -> None:
    """Note la dernière activité de l'utilisateur connecté (au plus toutes les 5 minutes)."""
    email = st.session_state.get("user_email", "")
    if not email or st.session_state.get("role") == "demo" or not _colonne_activite_prete():
        return
    maintenant = time.time()
    if maintenant - st.session_state.get("_activite_notee", 0) < INTERVALLE_ACTIVITE:
        return
    try:
        from utils.db_supabase import get_supabase
        get_supabase().table("users").update(
            {"last_seen": datetime.now(timezone.utc).isoformat()}).eq("email", email).execute()
        st.session_state["_activite_notee"] = maintenant
    except Exception:
        pass


# ─── Lecture des données ──────────────────────────────────────────────────────

def _date(v):
    """Texte ISO (base) → datetime avec fuseau, ou None."""
    if not v:
        return None
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _fr(d, heure=True):
    if not d:
        return "—"
    d = d.astimezone(PARIS)
    return d.strftime("%d/%m/%Y %H:%M" if heure else "%d/%m/%Y")


def _depuis(d, maintenant):
    """« En ligne », « il y a 3 h », « il y a 2 j »…"""
    if not d:
        return "Jamais"
    ecart = maintenant - d
    if ecart <= timedelta(minutes=EN_LIGNE_MINUTES):
        return "En ligne"
    minutes = int(ecart.total_seconds() // 60)
    if minutes < 60:
        return f"Il y a {minutes} min"
    if minutes < 24 * 60:
        return f"Il y a {minutes // 60} h"
    return f"Il y a {minutes // (24 * 60)} j"


def _charger():
    from utils.db_supabase import get_supabase
    sb = get_supabase()
    colonnes = "email, nom, cabinet, role, plan, is_active, last_login, created_at, tenant_id"
    if _colonne_activite_prete():
        colonnes += ", last_seen"
    users = sb.table("users").select(colonnes).order("created_at", desc=True).execute().data or []
    cabinets = {str(c["id"]): c for c in (sb.table("smd_cabinets")
                                          .select("id, nom, plan, quota_used_month, quota_month")
                                          .execute().data or [])}
    journal = sb.table("audit_logs").select("action, module, details, created_at") \
        .order("created_at", desc=True).limit(100).execute().data or []
    return users, cabinets, journal


# ─── Page ─────────────────────────────────────────────────────────────────────

def page_supervision():
    import pandas as pd
    from utils.auth_rbac import get_role_label

    st.title("Supervision")
    if st.session_state.get("role") != "admin":
        st.error("Page réservée à l'administrateur de la plateforme.", icon=":material/lock:")
        return

    c1, c2 = st.columns([4, 1])
    c1.caption(f"« En ligne » : activité depuis moins de {EN_LIGNE_MINUTES} minutes. "
               "L'activité est notée au plus toutes les 5 minutes.")
    c2.button("Actualiser", icon=":material/refresh:", width="stretch", key="sup_actualiser")

    try:
        users, cabinets, journal = _charger()
    except Exception:
        st.error("Base de données injoignable : supervision indisponible pour le moment.", icon=":material/error:")
        return

    maintenant = datetime.now(timezone.utc)
    aujourd_hui = maintenant.astimezone(PARIS).date()
    debut_mois = maintenant.astimezone(PARIS).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    mois = maintenant.astimezone(PARIS).strftime("%Y-%m")

    lignes, en_ligne, actifs_jour, actifs_7j, nouveaux = [], 0, 0, 0, 0
    for u in users:
        vu = _date(u.get("last_seen")) or None
        connexion = _date(u.get("last_login"))
        derniere = max([d for d in (vu, connexion) if d], default=None)
        cree = _date(u.get("created_at"))
        if derniere and maintenant - derniere <= timedelta(minutes=EN_LIGNE_MINUTES):
            en_ligne += 1
        if derniere and derniere.astimezone(PARIS).date() == aujourd_hui:
            actifs_jour += 1
        if derniere and maintenant - derniere <= timedelta(days=7):
            actifs_7j += 1
        if cree and cree >= debut_mois:
            nouveaux += 1
        cab = cabinets.get(str(u.get("tenant_id") or ""), {})
        quota = (cab.get("quota_used_month") or 0) if cab.get("quota_month") == mois else 0
        lignes.append({
            "État": _depuis(derniere, maintenant),
            "E-mail": u.get("email", ""),
            "Nom": u.get("nom") or "",
            "Cabinet": cab.get("nom") or u.get("cabinet") or "",
            "Rôle": get_role_label(u.get("role", "")),
            "Plan": (cab.get("plan") or u.get("plan") or "").capitalize(),
            "Analyses du cabinet ce mois": quota,
            "Dernière activité": _fr(derniere),
            "Inscrit le": _fr(cree, heure=False),
            "Compte actif": "Oui" if u.get("is_active", True) else "Non",
            "_tri": derniere or datetime.min.replace(tzinfo=timezone.utc),
        })

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("En ligne maintenant", en_ligne)
    m2.metric("Actifs aujourd'hui", actifs_jour)
    m3.metric("Actifs sur 7 jours", actifs_7j)
    m4.metric("Nouveaux comptes ce mois", nouveaux)

    st.subheader("Utilisateurs")
    recherche = st.text_input("Rechercher (e-mail, nom ou cabinet)", key="sup_recherche",
                              placeholder="ex. cabinet-martin.fr")
    df = pd.DataFrame(lignes)
    if not df.empty:
        df = df.sort_values("_tri", ascending=False).drop(columns="_tri")
        if recherche:
            r = recherche.lower()
            df = df[df[["E-mail", "Nom", "Cabinet"]].apply(lambda s: s.str.lower().str.contains(r, regex=False)).any(axis=1)]
        st.caption(f"{len(df)} compte(s) sur {len(lignes)}")
        st.dataframe(df, hide_index=True, width="stretch")
    else:
        st.info("Aucun compte enregistré.")

    st.subheader("Journal des dernières actions")
    st.caption("100 dernières actions : connexions, inscriptions, analyses lancées, sauvegardes, dossiers.")
    jl = []
    for j in journal:
        det = j.get("details") or {}
        if not isinstance(det, dict):
            det = {}
        detail = det.get("details") or det.get("detail") or det.get("resource") or ""
        jl.append({
            "Date": _fr(_date(j.get("created_at"))),
            "Action": ACTIONS.get(j.get("action", ""), j.get("action", "")),
            "Utilisateur": det.get("user_email", ""),
            "Détail": detail,
        })
    if jl:
        st.dataframe(pd.DataFrame(jl), hide_index=True, width="stretch")
    else:
        st.info("Aucune action enregistrée pour le moment.")
