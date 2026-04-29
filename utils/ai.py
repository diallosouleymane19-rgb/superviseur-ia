import requests
import json
import os

API_KEY = os.getenv("MISTRAL_API_KEY")
MODEL = "mistral-large-latest"


def appel_mistral(contenu):
    url = "https://api.mistral.ai/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Tu es un expert-comptable français."},
            {"role": "user", "content": contenu}
        ]
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    result = response.json()

    return result["choices"][0]["message"]["content"]


def extraire_contenu_mistral(texte):
    return texte.strip()


def parse_montant(texte):
    import re
    match = re.search(r"(\d+[.,]\d{2})", texte)
    if match:
        return float(match.group(1).replace(",", "."))
    return 0.0


def extraire_compte_valide(texte):
    import re
    match = re.search(r"\b(6\d{2}|7\d{2})\b", texte)
    if match:
        return match.group(1)
    return "000"

