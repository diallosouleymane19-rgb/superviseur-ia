# -*- coding: utf-8 -*-
"""
utils/mot_de_passe_oublie.py - SMD Global Consulting LLC
Réinitialisation du mot de passe par e-mail.

1. La personne saisit son e-mail : si un compte actif existe, un lien à usage unique valable 1 heure
   lui est envoyé. Le message affiché est le même que le compte existe ou non (on ne révèle pas
   quelles adresses sont inscrites). Au plus 3 demandes par heure et par adresse.
2. Le lien ouvre l'application avec ?reset=<jeton> : nouveau mot de passe (mêmes règles qu'à
   l'inscription), enregistré chiffré (bcrypt). Le jeton est ensuite inutilisable.
Seule l'empreinte SHA-256 du jeton est stockée en base : une fuite de la base ne donne aucun lien valable.
"""
import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

import streamlit as st

VALIDITE_MINUTES = 60
MAX_DEMANDES_HEURE = 3


@st.cache_resource(show_spinner=False)
def _table_prete() -> bool:
    try:
        from utils.db_supabase import _database_url, get_supabase
        if not _database_url():
            return False
        from psycopg import sql
        sb = get_supabase()
        sb._lire(sql.SQL("CREATE TABLE IF NOT EXISTS password_resets ("
                         "token_hash text PRIMARY KEY, email text NOT NULL, "
                         "expires_at timestamptz NOT NULL, used_at timestamptz, "
                         "created_at timestamptz NOT NULL DEFAULT now())"), [])
        sb._cache_types.pop("password_resets", None)
        return True
    except Exception:
        return False


def disponible() -> bool:
    from utils.email_envoi import envoi_possible
    return _table_prete() and envoi_possible()


def _empreinte(jeton: str) -> str:
    return hashlib.sha256(jeton.encode("utf-8")).hexdigest()


def _maintenant():
    return datetime.now(timezone.utc)


def mdp_fort(mdp: str):
    if len(mdp) < 8:
        return False, "8 caractères minimum"
    if not re.search(r"[A-Z]", mdp):
        return False, "au moins une majuscule"
    if not re.search(r"[0-9]", mdp):
        return False, "au moins un chiffre"
    return True, ""


def _adresse_app() -> str:
    try:
        url = st.secrets.get("APP_URL", "")
    except Exception:
        url = ""
    return (url or "https://app.smdconsulting.pro").rstrip("/")


def demander(email: str) -> None:
    """Crée un jeton et envoie le lien si le compte existe et n'a pas dépassé la limite. Ne révèle rien."""
    email = (email or "").strip().lower()
    if not email or not disponible():
        return
    from utils.auth_rbac import get_user, log_action
    from utils.db_supabase import get_supabase
    user = get_user(email)
    if not user or user.get("is_active") is False:
        return
    sb = get_supabase()
    il_y_a_1h = (_maintenant() - timedelta(hours=1)).isoformat()
    n = sb.table("password_resets").select("token_hash", count="exact").eq("email", email) \
        .gte("created_at", il_y_a_1h).execute().count or 0
    if n >= MAX_DEMANDES_HEURE:
        return
    jeton = secrets.token_urlsafe(32)
    sb.table("password_resets").insert({
        "token_hash": _empreinte(jeton), "email": email,
        "expires_at": (_maintenant() + timedelta(minutes=VALIDITE_MINUTES)).isoformat(),
    }).execute()
    lien = f"{_adresse_app()}/?reset={jeton}"
    from utils.email_envoi import envoyer_email
    ok = envoyer_email(email, "KontrolIA : réinitialisation de votre mot de passe", (
        "Bonjour,\n\n"
        "Vous avez demandé à réinitialiser le mot de passe de votre compte KontrolIA.\n"
        f"Ouvrez ce lien pour choisir un nouveau mot de passe (valable {VALIDITE_MINUTES} minutes, une seule fois) :\n\n"
        f"{lien}\n\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez cet e-mail : votre mot de passe actuel reste valable.\n\n"
        "KontrolIA — SMD Global Consulting LLC\ncontact@smdconsulting.pro\n"))
    log_action(email, "MDP_DEMANDE", details="Lien envoyé" if ok else "Échec de l'envoi de l'e-mail")


def jeton_valide(jeton: str):
    """Retourne l'e-mail du compte si le jeton est valable, sinon None."""
    if not jeton or not _table_prete():
        return None
    from utils.db_supabase import get_supabase
    lignes = get_supabase().table("password_resets").select("email, expires_at, used_at") \
        .eq("token_hash", _empreinte(jeton)).limit(1).execute().data or []
    if not lignes or lignes[0].get("used_at"):
        return None
    expire = datetime.fromisoformat(str(lignes[0]["expires_at"]).replace("Z", "+00:00"))
    if expire.tzinfo is None:
        expire = expire.replace(tzinfo=timezone.utc)
    return lignes[0]["email"] if expire > _maintenant() else None


def appliquer(jeton: str, nouveau: str) -> bool:
    """Enregistre le nouveau mot de passe et invalide le jeton (et les autres liens du compte)."""
    email = jeton_valide(jeton)
    if not email:
        return False
    import bcrypt
    from utils.auth_rbac import log_action
    from utils.db_supabase import get_supabase
    sb = get_supabase()
    pw = bcrypt.hashpw(nouveau.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    sb.table("users").update({"password_hash": pw, "updated_at": _maintenant().isoformat()}).eq("email", email).execute()
    sb.table("password_resets").update({"used_at": _maintenant().isoformat()}).eq("email", email).is_("used_at", "null").execute()
    try:
        from utils.securite_connexion import effacer_echecs
        effacer_echecs(email)
    except Exception:
        pass
    log_action(email, "MDP_REINITIALISE", details="Nouveau mot de passe enregistré")
    return True


# ─── Écrans ───────────────────────────────────────────────────────────────────

def formulaire_demande() -> None:
    """Sous le formulaire de connexion : « Mot de passe oublié ? »."""
    with st.expander("Mot de passe oublié ?"):
        if not disponible():
            st.caption("Écrivez à contact@smdconsulting.pro depuis l'adresse de votre compte : "
                       "nous vous aiderons à retrouver l'accès.")
            return
        with st.form("form_mdp_oublie", border=False):
            email = st.text_input("Votre e-mail professionnel", key="mdp_oublie_email")
            envoye = st.form_submit_button("Recevoir un lien de réinitialisation", width="stretch")
        if envoye:
            demander(email)
            st.success("Si un compte existe pour cette adresse, un e-mail vient d'être envoyé avec un lien "
                       f"valable {VALIDITE_MINUTES} minutes. Pensez à regarder vos courriers indésirables.",
                       icon=":material/mark_email_read:")


def page_reinitialisation(jeton: str) -> None:
    """Page ouverte depuis le lien reçu par e-mail (?reset=…)."""
    st.title("Nouveau mot de passe")
    if st.session_state.get("mdp_reinitialise"):
        st.success("Votre mot de passe a été changé. Vous pouvez vous connecter.", icon=":material/check_circle:")
        if st.button("Aller à la connexion", type="primary"):
            st.session_state.pop("mdp_reinitialise", None)
            st.query_params.clear()
            st.rerun()
        return
    email = jeton_valide(jeton)
    if not email:
        st.error("Ce lien n'est plus valable : il a déjà servi ou a expiré. Refaites une demande depuis la page "
                 "de connexion (« Mot de passe oublié ? »).", icon=":material/error:")
        if st.button("Retour à la connexion"):
            st.query_params.clear()
            st.rerun()
        return
    st.caption(f"Compte : {email}")
    with st.form("form_nouveau_mdp"):
        mdp = st.text_input("Nouveau mot de passe", type="password", help="8 caractères minimum, 1 majuscule, 1 chiffre")
        mdp2 = st.text_input("Confirmer le nouveau mot de passe", type="password")
        ok = st.form_submit_button("Enregistrer le nouveau mot de passe", type="primary", width="stretch")
    if ok:
        fort, msg = mdp_fort(mdp)
        if mdp != mdp2:
            st.error("Les deux mots de passe ne correspondent pas.", icon=":material/error:")
        elif not fort:
            st.error(f"Mot de passe trop faible : {msg}.", icon=":material/error:")
        elif appliquer(jeton, mdp):
            st.session_state["mdp_reinitialise"] = True
            st.rerun()
        else:
            st.error("Ce lien n'est plus valable. Refaites une demande.", icon=":material/error:")
