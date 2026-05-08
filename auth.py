# -*- coding: utf-8 -*-
"""Module d'authentification - SMD Consulting"""
import streamlit as st
import os

def login(email, password):
    """Authentifie un utilisateur"""
    # Identifiants (depuis .env ou valeurs par défaut)
    valid_email = "smdconsulting@gmail.com"
    valid_password = "SMDConsulting2026!"

    if email.strip() == valid_email and password.strip() == valid_password:
        st.session_state["authenticated"] = True
        st.session_state["user_email"] = email
        return True
    return False

def is_connecte():
    """Vérifie si l'utilisateur est authentifié"""
    return st.session_state.get("authenticated", False)

def logout():
    """Déconnexion de l'utilisateur"""
    st.session_state["authenticated"] = False
    st.session_state["user_email"] = None