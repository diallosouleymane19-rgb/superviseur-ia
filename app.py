import os
import requests

API_KEY = os.getenv("MISTRAL_API_KEY")
API_URL = "https://api.mistral.ai/v1/chat/completions"

def appel_mistral(messages):
    """
    Appel générique à Mistral.
    Supporte :
    - messages texte
    - messages multimodaux (OCR)
    Retourne toujours un dict propre.
    """

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "pixtral-large-latest",
        "messages": messages,
        "temperature": 0.2
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers)

        # Vérification HTTP
        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}", "details": response.text}

        data = response.json()

        # Vérification structure
        if "choices" not in data:
            return {"error": "Réponse inattendue", "details": data}

        return data

    except Exception as e:
        return {"error": str(e)}


def extraire_contenu_mistral(data):
    """
    Extrait le texte d'une réponse Mistral.
    Gère les erreurs proprement.
    """

    if not isinstance(data, dict):
        return "❌ Erreur : réponse IA invalide."

    if "error" in data:
        return f"❌ Erreur IA : {data['error']}"

    try:
        return data["choices"][0]["message"]["content"]
    except:
        return "❌ Erreur : impossible d'extraire le contenu IA."
