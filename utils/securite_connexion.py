# -*- coding: utf-8 -*-
"""
utils/securite_connexion.py - SMD Global Consulting LLC
Protection contre les essais répétés de mot de passe :
après 5 échecs en 15 minutes sur une même adresse, la connexion est refusée pendant 15 minutes,
même avec le bon mot de passe. Les échecs sont gardés en base (table login_echecs) pour tenir
même si la personne recharge la page ; à défaut de base, un compteur par session prend le relais.
"""
import time
from datetime import datetime, timedelta, timezone

import streamlit as st

MAX_ECHECS = 5
FENETRE_MINUTES = 15


@st.cache_resource(show_spinner=False)
def _table_prete() -> bool:
    """Crée la table des échecs si elle manque (base OVH). Sans effet sur les autres données."""
    try:
        from utils.db_supabase import _database_url, get_supabase
        if not _database_url():
            return False
        from psycopg import sql
        sb = get_supabase()
        sb._lire(sql.SQL("CREATE TABLE IF NOT EXISTS login_echecs ("
                         "id bigserial PRIMARY KEY, email text NOT NULL, "
                         "created_at timestamptz NOT NULL DEFAULT now())"), [])
        sb._lire(sql.SQL("CREATE INDEX IF NOT EXISTS login_echecs_email_idx ON login_echecs (email, created_at)"), [])
        return True
    except Exception:
        return False


def _depuis():
    return (datetime.now(timezone.utc) - timedelta(minutes=FENETRE_MINUTES)).isoformat()


def _echecs_session(email: str) -> list:
    tous = st.session_state.setdefault("_login_echecs", {})
    limite = time.time() - FENETRE_MINUTES * 60
    tous[email] = [t for t in tous.get(email, []) if t > limite]
    return tous[email]


def est_bloque(email: str) -> bool:
    """Vrai si l'adresse a atteint le nombre maximal d'échecs dans la fenêtre."""
    email = (email or "").strip().lower()
    if not email:
        return False
    if len(_echecs_session(email)) >= MAX_ECHECS:
        return True
    if _table_prete():
        try:
            from utils.db_supabase import get_supabase
            n = get_supabase().table("login_echecs").select("id", count="exact") \
                .eq("email", email).gte("created_at", _depuis()).execute().count or 0
            return n >= MAX_ECHECS
        except Exception:
            pass
    return False


def noter_echec(email: str) -> None:
    email = (email or "").strip().lower()
    if not email:
        return
    _echecs_session(email).append(time.time())
    if _table_prete():
        try:
            from utils.db_supabase import get_supabase
            get_supabase().table("login_echecs").insert({"email": email}).execute()
        except Exception:
            pass
    try:
        from utils.auth_rbac import log_action
        log_action(email, "LOGIN_ECHEC", details="Mot de passe incorrect ou compte inconnu")
    except Exception:
        pass


def effacer_echecs(email: str) -> None:
    """Après une connexion réussie : remet le compteur à zéro."""
    email = (email or "").strip().lower()
    st.session_state.setdefault("_login_echecs", {}).pop(email, None)
    if _table_prete():
        try:
            from utils.db_supabase import get_supabase
            get_supabase().table("login_echecs").delete().eq("email", email).execute()
        except Exception:
            pass


def purger_anciens() -> None:
    """Supprime les échecs de plus d'un jour (appelé avec les autres purges)."""
    if _table_prete():
        try:
            from utils.db_supabase import get_supabase
            hier = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            get_supabase().table("login_echecs").delete().lt("created_at", hier).execute()
        except Exception:
            pass
