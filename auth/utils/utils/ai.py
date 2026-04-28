import requests
import re
import json
from datetime import datetime
import streamlit as st

# ---------------- API MISTRAL ---------------- #

def get_api_key():
    """
    Récupère la clé API Mistral depuis .streamlit/secrets.toml
    """
    try:
        return st.secrets["MISTRAL_API_KEY"]
    except (KeyError, FileNotFoundError):
        st.error("⚠️ Clé API manquante. Ajoutez MISTRAL_API_KEY dans .streamlit/secrets.toml")
        st.stop()

def appel_mistral(messages: list, json_mode: bool = False, timeout: int = 30) -> dict:
    """
    Appel générique à l'API Mistral.
    """
    API_KEY = get_api_key()
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    payload = {
        "model": "mistral-small-latest",
        "messages": messages
    }

    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()

def extraire_contenu_mistral(result: dict) -> str:
    """
    Extrait le texte du message retourné par Mistral.
    """
    try:
        msg = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return ""

    if isinstance(msg, str):
        return msg

    if isinstance(msg, list):
        for part in msg:
            if isinstance(part, dict) and part.get("type") == "text":
                return part.get("text", "")

    return ""

# ---------------- MONTANTS ---------------- #

def parse_montant(val) -> float:
    """
    Convertit un montant texte en float.
    Gère : €, espaces, virgules, points multiples.
    """
    if isinstance(val, (int, float)):
        return float(val)

    cleaned = re.sub(r"[€$£\s]", "", str(val))
    cleaned = cleaned.replace(",", ".")
    cleaned = re.sub(r"\.(?=.*\.)", "", cleaned)

    try:
        return float(cleaned)
    except ValueError:
        return 0.0

# ---------------- COMPTES COMPTABLES ---------------- #

def extraire_compte_valide(valeur) -> str:
    """
    Extrait un compte comptable valide (6 chiffres).
    Gère : dict, int, float, string, formats mélangés.
    """
    if isinstance(valeur, dict):
        if "compte" in valeur:
            valeur = valeur["compte"]
        elif "suggestion" in valeur:
            valeur = valeur["suggestion"]
        else:
            for _, v in valeur.items():
                if isinstance(v, str) and re.match(r"^\d{6}$", v):
                    return v
            return "606300"

    if isinstance(valeur, (int, float)):
        return f"{int(valeur):06d}"

    if isinstance(valeur, str):
        cleaned = re.sub(r"[^0-9]", "", valeur)
        if len(cleaned) >= 6:
            return cleaned[:6]

    return "606300"

