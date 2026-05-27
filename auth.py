# -*- coding: utf-8 -*-
"""
auth.py — Superviseur IA PCG France
Authentification : RBAC (smd_users.db) en priorité → st.secrets en fallback.
"""

import streamlit as st
import bcrypt
from datetime import datetime, timedelta


# ─── Helpers internes ─────────────────────────────────────────────────────────

def _set_session(email: str, role: str, nom: str, plan: str = "free",
                 cabinet: str = "", pays: str = "FR") -> None:
    """Hydrate st.session_state après connexion réussie."""
    st.session_state["authenticated"] = True
    st.session_state["user_email"]    = email
    st.session_state["role"]          = role
    st.session_state["nom"]           = nom
    st.session_state["plan"]          = plan
    st.session_state["cabinet"]       = cabinet
    st.session_state["pays_user"]     = pays
    st.session_state["login_time"]    = datetime.now().isoformat()


def _hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.strip().encode("utf-8"), bcrypt.gensalt())


def _verify_password(plain: str, hashed: bytes) -> bool:
    try:
        return bcrypt.checkpw(plain.strip().encode("utf-8"), hashed)
    except Exception:
        return False


# ─── LOGIN ────────────────────────────────────────────────────────────────────

def login(email: str, password: str) -> bool:
    """
    Authentification en 2 étapes :
    1. Base RBAC (smd_users.db) — utilisateurs enregistrés
    2. st.secrets (AUTH_EMAIL / AUTH_PASSWORD) — admin SMD fallback
    """
    email = email.strip().lower()

    # ── Étape 1 : base RBAC ──────────────────────────────────────────────────
    try:
        from utils.auth_rbac import verifier_login
        user = verifier_login(email, password)
        if user:
            _set_session(
                email   = user["email"],
                role    = user.get("role", "client"),
                nom     = user.get("nom") or email.split("@")[0],
                plan    = user.get("plan", "free"),
                cabinet = user.get("cabinet", ""),
                pays    = user.get("pays", "FR"),
            )
            # Audit log
            try:
                from utils.auth_rbac import log_action
                log_action(email, "login", app="pcg")
            except Exception:
                pass
            return True
    except Exception:
        pass

    # ── Étape 2 : st.secrets (admin SMD uniquement) ──────────────────────────
    try:
        auth_email = st.secrets.get("AUTH_EMAIL", "")
        auth_pw    = st.secrets.get("AUTH_PASSWORD", "")
        if auth_email and email == auth_email.strip().lower():
            if password.strip() == auth_pw:
                _set_session(
                    email   = email,
                    role    = st.secrets.get("AUTH_ROLE", "admin"),
                    nom     = st.secrets.get("AUTH_NOM", "SMD Consulting"),
                    plan    = "enterprise",
                )
                return True
        # Compte secondaire optionnel
        if "AUTH_EMAIL_2" in st.secrets:
            auth_email2 = st.secrets.get("AUTH_EMAIL_2", "")
            auth_pw2    = st.secrets.get("AUTH_PASSWORD_2", "")
            if email == auth_email2.strip().lower() and password.strip() == auth_pw2:
                _set_session(
                    email   = email,
                    role    = st.secrets.get("AUTH_ROLE_2", "cabinet"),
                    nom     = st.secrets.get("AUTH_NOM_2", "Utilisateur"),
                    plan    = "pro",
                )
                return True
    except Exception:
        pass

    return False


# ─── SESSION ──────────────────────────────────────────────────────────────────

def is_connecte() -> bool:
    """Vérifie si une session valide est active (timeout 8h)."""
    if not st.session_state.get("authenticated", False):
        return False
    login_time = st.session_state.get("login_time")
    if login_time:
        try:
            delta = datetime.now() - datetime.fromisoformat(login_time)
            if delta.total_seconds() > 28800:  # 8 heures
                logout()
                st.warning("⏰ Session expirée. Veuillez vous reconnecter.")
                return False
        except Exception:
            pass
    return True


def logout() -> None:
    """Déconnexion complète."""
    keys = ["authenticated", "user_email", "role", "nom", "plan",
            "cabinet", "pays_user", "login_time"]
    for key in keys:
        st.session_state.pop(key, None)
    st.rerun()


# ─── Accesseurs session ───────────────────────────────────────────────────────

def get_role() -> str:
    return st.session_state.get("role", "client")


def get_nom() -> str:
    return st.session_state.get("nom", "Utilisateur")


def get_plan() -> str:
    return st.session_state.get("plan", "free")


def is_admin() -> bool:
    return get_role() == "admin"


def is_cabinet() -> bool:
    return get_role() in ("admin", "cabinet")
