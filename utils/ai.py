import requests
import json
import os

# Récupération de la clé API depuis Streamlit Cloud ou .env
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

def appel_mistral(prompt):
    """
    Envoie un prompt texte au modèle Mistral et retourne la réponse brute.
    """

    url = "https://api.mistral.ai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "mistral-large-latest",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        return f"Erreur IA : HTTP {response.status_code}"

    data = response.json()
    return data["choices"][0]["message"]["content"]


def extraire_contenu_mistral(texte):
    """
    Si jamais tu veux parser un JSON retourné par Mistral.
    """
    try:
        return json.loads(texte)
    except:
        return texte
fix ai.py
