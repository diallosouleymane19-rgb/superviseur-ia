# -*- coding: utf-8 -*-
"""
utils/db_supabase.py - SMD Consulting
Client Supabase partagé (service role) pour PCG France & SYSCOHADA.

Secrets requis dans .streamlit/secrets.toml :
    SUPABASE_URL         = "https://ckfzczuvjbxgrwgpqrdz.supabase.co"
    SUPABASE_SERVICE_KEY = "eyJ..."   # service_role depuis Dashboard → Settings → API

Le service_role key bypasse les RLS policies — usage SERVEUR uniquement.
Ne jamais l'exposer côté client / dans le HTML.
"""
import os

_SUPABASE_CLIENT = None   # singleton


def get_supabase():
    """
    Retourne un client Supabase authentifié (service role).
    Singleton mis en cache pour éviter de recréer la connexion à chaque rerun.
    """
    global _SUPABASE_CLIENT
    if _SUPABASE_CLIENT is not None:
        return _SUPABASE_CLIENT

    url, key = _load_credentials()
    if not url or not key:
        raise ValueError(
            "Supabase non configuré. Ajoutez SUPABASE_URL et SUPABASE_SERVICE_KEY "
            "dans .streamlit/secrets.toml ou les variables d'environnement."
        )

    try:
        from supabase import create_client
        _SUPABASE_CLIENT = create_client(url, key)
        return _SUPABASE_CLIENT
    except ImportError:
        raise ImportError(
            "Package 'supabase' manquant. Ajoutez 'supabase>=2.4.0' dans requirements.txt."
        )


def _load_credentials() -> tuple:
    """Charge URL + clé depuis st.secrets ou variables d'environnement."""
    try:
        import streamlit as st
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_SERVICE_KEY",
              st.secrets.get("SUPABASE_KEY", ""))
        if url and key:
            return url, key
    except Exception:
        pass
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_KEY", ""))
    return url, key


def supabase_disponible() -> bool:
    """Retourne True si Supabase est correctement configuré."""
    try:
        url, key = _load_credentials()
        return bool(url and key)
    except Exception:
        return False
