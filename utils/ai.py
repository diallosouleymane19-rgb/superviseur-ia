import requests
import json
import os

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

def appel_mistral(prompt):
    """
    Accepte un texte simple ou une liste de messages (pour les images).
    """
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    # Si prompt est une liste de messages (OCR image), on l'utilise directement
    if isinstance(prompt, list):
        messages = prompt
        model = "pixtral-12b-2409"
    else:
        messages = [{"role": "user", "content": prompt}]
        model = "mistral-large-latest"

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        return f"Erreur IA : HTTP {response.status_code} - {response.text}"
    data = response.json()
    return data["choices"][0]["message"]["content"]


def extraire_contenu_mistral(texte):
    """
    Retourne le texte tel quel ou parse le JSON si possible.
    """
    try:
        return json.loads(texte)
    except:
        return texte