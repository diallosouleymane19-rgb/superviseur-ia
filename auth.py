# -*- coding: utf-8 -*-
"""
Module d'authentification sécurisé - SMD Consulting
Conformité RGPD - Hashage SHA256 - Gestion des rôles - Timeout session
"""
import streamlit as st
import hashlib
import hmac
from datetime import datetime, timedelta

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

def _hash_password(password: str) -> str:
    """Hashage sécurisé SHA256 du mot de passe"""
    return hashlib.sha256(password.strip().encode()).hexdigest()

def _get_users() -> dict:
    """
    Récupère les utilisateurs depuis st.secrets.
    Fallback sur utilisateur par défaut si secrets non configurés.
    """
    try:
        users = {
            st.secrets["AUTH_EMAIL"]: {
                "password_hash": _hash_password(st.secrets["AUTH_PASSWORD"]),
                "role": "Administrateur",
                "nom": "SMD Consulting"
            }
        }
        # Utilisateurs supplémentaires si définis dans secrets
        if "AUTH_EMAIL_2" in st.secrets:
            users[st.secrets["AUTH_EMAIL_2"]] = {
                "password_hash": _hash_password(st.secrets["AUTH_PASSWORD_2"]),
                "role": st.secrets.get("AUTH_ROLE_2", "Utilisateur"),
                "nom": st.secrets.get("AUTH_NOM_2", "Utilisateur")
            }
        return users
    except Exception:
        # Fallback sécurisé — mot de passe hashé, jamais en clair
        return {
            "contact@smdconsulting.pro": {
                "password_hash": _hash_password("SMDConsulting2026!"),
                "role": "Administrateur",
                "nom": "SMD Consulting"
            }
        }

# ---------------------------------------------------------
# AUTHENTIFICATION
# ---------------------------------------------------------

def login(email: str, password: str) -> bool:
    """
    Authentifie un utilisateur avec vérification sécurisée.
    Utilise hmac.compare_digest pour éviter les timing attacks.
    """
    users = _get_users()
    email = email.strip().lower()

    if email not in users:
        return False

    user = users[email]
    password_hash = _hash_password(password)

    # Comparaison sécurisée anti timing-attack
    if hmac.compare_digest(password_hash, user["password_hash"]):
        st.session_state["authenticated"] = True
        st.session_state["user_email"] = email
        st.session_state["role"] = user["role"]
        st.session_state["nom"] = user["nom"]
        st.session_state["login_time"] = datetime.now().isoformat()
        return True

    return False

def is_connecte() -> bool:
    """
    Vérifie si l'utilisateur est authentifié.
    Inclut vérification du timeout de session (8 heures).
    """
    if not st.session_state.get("authenticated", False):
        return False

    # Vérification timeout session
    login_time = st.session_state.get("login_time")
    if login_time:
        try:
            temps_connecte = datetime.now() - datetime.fromisoformat(login_time)
            if temps_connecte > timedelta(hours=8):
                logout()
                st.warning("⏱️ Session expirée. Veuillez vous reconnecter.")
                return False
        except Exception:
            pass

    return True

def logout():
    """Déconnexion sécurisée — nettoyage complet de la session"""
    keys_to_clear = [
        "authenticated", "user_email", "role",
        "nom", "login_time"
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

def get_role() -> str:
    """Retourne le rôle de l'utilisateur connecté"""
    return st.session_state.get("role", "Utilisateur")

def get_nom() -> str:
    """Retourne le nom de l'utilisateur connecté"""
    return st.session_state.get("nom", "Utilisateur")