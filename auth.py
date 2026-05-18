# -*- coding: utf-8 -*-
import streamlit as st
import bcrypt
from datetime import datetime, timedelta

def _hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.strip().encode('utf-8'), bcrypt.gensalt())

def _verify_password(plain: str, hashed: bytes) -> bool:
    try:
        return bcrypt.checkpw(plain.strip().encode('utf-8'), hashed)
    except Exception:
        return False

def _get_users() -> dict:
    try:
        users = {
            st.secrets['AUTH_EMAIL']: {
                'password_hash': _hash_password(st.secrets['AUTH_PASSWORD']),
                'role': st.secrets.get('AUTH_ROLE', 'Administrateur'),
                'nom': st.secrets.get('AUTH_NOM', 'SMD Consulting')
            }
        }
        if 'AUTH_EMAIL_2' in st.secrets:
            users[st.secrets['AUTH_EMAIL_2']] = {
                'password_hash': _hash_password(st.secrets['AUTH_PASSWORD_2']),
                'role': st.secrets.get('AUTH_ROLE_2', 'Utilisateur'),
                'nom': st.secrets.get('AUTH_NOM_2', 'Utilisateur')
            }
        return users
    except KeyError as e:
        raise RuntimeError(f'Secret manquant : {e}. Configurez AUTH_EMAIL et AUTH_PASSWORD.')

def login(email: str, password: str) -> bool:
    try:
        users = _get_users()
    except RuntimeError as e:
        st.error(str(e))
        return False
    email = email.strip().lower()
    if email not in users:
        return False
    user = users[email]
    if _verify_password(password, user['password_hash']):
        st.session_state['authenticated'] = True
        st.session_state['user_email'] = email
        st.session_state['role'] = user['role']
        st.session_state['nom'] = user['nom']
        st.session_state['login_time'] = datetime.now().isoformat()
        return True
    return False

def is_connecte() -> bool:
    if not st.session_state.get('authenticated', False):
        return False
    login_time = st.session_state.get('login_time')
    if login_time:
        try:
            delta = datetime.now() - datetime.fromisoformat(login_time)
            if delta.total_seconds() > 28800:
                logout()
                st.warning('Session expiree. Veuillez vous reconnecter.')
                return False
        except Exception:
            pass
    return True

def logout():
    for key in ['authenticated', 'user_email', 'role', 'nom', 'login_time']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

def get_role() -> str:
    return st.session_state.get('role', 'Utilisateur')

def get_nom() -> str:
    return st.session_state.get('nom', 'Utilisateur')
