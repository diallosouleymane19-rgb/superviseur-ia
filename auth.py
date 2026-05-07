# -*- coding: utf-8 -*-
"""Module d'authentification - SMD Consulting"""
import streamlit as st


def login(email, password):
    """
    Authentifie un utilisateur
    
    Args:
        email: Email de l'utilisateur
        password: Mot de passe
        
    Returns:
        True si authentification réussie, False sinon
    """
    # Identifiants valides (par défaut)
    VALID_EMAIL = "smdconsulting@gmail.com"
    VALID_PASSWORD = "SMDConsulting2026!"
    
    # Tentative de récupération depuis secrets (Streamlit Cloud)
    try:
        valid_email = st.secrets.get("USER_EMAIL", VALID_EMAIL)
        valid_password = st.secrets.get("USER_PASSWORD", VALID_PASSWORD)
    except:
        valid_email = VALID_EMAIL
        valid_password = VALID_PASSWORD
    
    # Vérification
    if email == valid_email and password == valid_password:
        st.session_state["authenticated"] = True
        st.session_state["user_email"] = email
        return True
    else:
        return False


def is_connecte():
    """Vérifie si l'utilisateur est authentifié"""
    return st.session_state.get("authenticated", False)


def logout():
    """Déconnexion de l'utilisateur"""
    st.session_state["authenticated"] = False
    st.session_state["user_email"] = None