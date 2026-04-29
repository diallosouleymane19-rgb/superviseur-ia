import requests
import os

def appel_mistral(prompt: str) -> str:
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        return "❌ Clé API Mistral manquante. Vérifie ton fichier .env"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistral-small-latest",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 1500
    }

    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        return "❌ Timeout : Mistral met trop de temps à répondre."
    except requests.exceptions.HTTPError as e:
        return f"❌ Erreur HTTP Mistral : {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"❌ Erreur inattendue : {str(e)}"


def analyse_balance_ai(df):
    balance_txt = df.head(50).to_string()
    prompt = f"""
Tu es un expert-comptable français. Analyse la balance suivante :
{balance_txt}

Donne une analyse structurée comprenant :
- points forts
- anomalies
- comptes à surveiller
- suggestions de régularisation
- risques fiscaux
- cohérence des soldes
- remarques professionnelles

Réponds en texte clair, structuré et professionnel.
    """
    reponse = appel_mistral(prompt)
    return reponse