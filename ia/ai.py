import os
import json
import logging
import requests
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional, Dict

# ---------------------------------------------------------
# Configuration du logging
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Charger le fichier .env depuis la RACINE du projet
# ---------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# ---------------------------------------------------------
# Configuration & Constantes
# ---------------------------------------------------------
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
DEFAULT_MODEL = "mistral-large-latest"
DEFAULT_TEMPERATURE = 0.2
REQUEST_TIMEOUT = 30  # secondes

# ---------------------------------------------------------
# Validation de la clé API au démarrage
# ---------------------------------------------------------
def valider_cle_api() -> bool:
    """
    Valide que la clé API Mistral est présente et non vide.
    """
    if not MISTRAL_API_KEY or MISTRAL_API_KEY.strip() == "":
        logger.error("MISTRAL_API_KEY manquante ou vide dans le fichier .env")
        return False
    
    if not MISTRAL_API_KEY.startswith("sk-") and not MISTRAL_API_KEY.startswith("mistral-"):
        logger.warning("Format de clé API inhabituel - vérifiez votre clé")
    
    logger.info("Clé API Mistral chargée avec succès")
    return True

# ---------------------------------------------------------
# Fonction d'appel à l'API Mistral
# ---------------------------------------------------------
def appel_mistral(
    prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: Optional[int] = None
) -> Dict[str, any]:
    """
    Envoie un prompt texte au modèle Mistral et retourne la réponse.
    """
    if not valider_cle_api():
        return {
            "success": False,
            "content": None,
            "error": "Clé API Mistral invalide ou manquante"
        }
    
    if not prompt or prompt.strip() == "":
        return {
            "success": False,
            "content": None,
            "error": "Le prompt ne peut pas être vide"
        }
    
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature
    }
    
    if max_tokens:
        payload["max_tokens"] = max_tokens
    
    try:
        logger.info(f"Appel API Mistral - Modèle: {model}")
        response = requests.post(
            MISTRAL_API_URL,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code != 200:
            logger.error(f"Erreur HTTP {response.status_code}")
            return {"success": False, "content": None, "error": f"Erreur API: {response.status_code}"}
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return {
            "success": True,
            "content": content,
            "error": None,
            "usage": data.get("usage", {})
        }
    
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        return {"success": False, "content": None, "error": str(e)}

# ---------------------------------------------------------
# FONCTION CORRIGÉE : extraire_contenu_mistral
# ---------------------------------------------------------
def extraire_contenu_mistral(resultat_api: Dict[str, any]) -> str:
    """
    Extrait le texte de la réponse API de manière sécurisée pour l'OCR.
    """
    if resultat_api.get("success") and resultat_api.get("content"):
        return resultat_api["content"]
    
    error_msg = resultat_api.get("error", "Erreur inconnue")
    return f"Désolé, je n'ai pas pu analyser le document. Détails : {error_msg}"

# ---------------------------------------------------------
# Exemple d'utilisation (Test local)
# ---------------------------------------------------------
if __name__ == "__main__":
    result = appel_mistral(prompt="Bonjour")
    print(extraire_contenu_mistral(result))
