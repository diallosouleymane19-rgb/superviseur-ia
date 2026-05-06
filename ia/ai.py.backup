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
# Fonction d'appel à l'API Mistral (VERSION AMÉLIORÉE)
# ---------------------------------------------------------
def appel_mistral(
    prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: Optional[int] = None
) -> Dict[str, any]:
    """
    Envoie un prompt texte au modèle Mistral et retourne la réponse.
    
    Args:
        prompt: Le texte à envoyer au modèle
        model: Le modèle Mistral à utiliser
        temperature: Contrôle la créativité (0.0 à 1.0)
        max_tokens: Limite de tokens dans la réponse (optionnel)
    
    Returns:
        Dict avec 'success' (bool), 'content' (str) et 'error' (str optionnel)
    """
    # Validation de la clé API
    if not valider_cle_api():
        return {
            "success": False,
            "content": None,
            "error": "Clé API Mistral invalide ou manquante"
        }
    
    # Validation du prompt
    if not prompt or prompt.strip() == "":
        return {
            "success": False,
            "content": None,
            "error": "Le prompt ne peut pas être vide"
        }
    
    # Préparation de la requête
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
        logger.info(f"Appel API Mistral - Modèle: {model}, Temperature: {temperature}")
        
        # Appel API avec timeout
        response = requests.post(
            MISTRAL_API_URL,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT
        )
        
        # Gestion des erreurs HTTP
        if response.status_code == 401:
            logger.error("Erreur d'authentification - Clé API invalide")
            return {
                "success": False,
                "content": None,
                "error": "Clé API invalide ou expirée"
            }
        
        if response.status_code == 429:
            logger.error("Limite de taux dépassée")
            return {
                "success": False,
                "content": None,
                "error": "Trop de requêtes - limite API atteinte"
            }
        
        if response.status_code != 200:
            logger.error(f"Erreur HTTP {response.status_code}: {response.text}")
            return {
                "success": False,
                "content": None,
                "error": f"Erreur API: HTTP {response.status_code}"
            }
        
        # Parsing de la réponse JSON
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de parsing JSON: {e}")
            return {
                "success": False,
                "content": None,
                "error": "Réponse API invalide (JSON malformé)"
            }
        
        # Validation de la structure de la réponse
        if "choices" not in data or len(data["choices"]) == 0:
            logger.error("Structure de réponse inattendue")
            return {
                "success": False,
                "content": None,
                "error": "Structure de réponse API invalide"
            }
        
        # Extraction du contenu
        content = data["choices"][0]["message"]["content"]
        logger.info("Réponse reçue avec succès")
        
        return {
            "success": True,
            "content": content,
            "error": None,
            "usage": data.get("usage", {})  # Informations sur les tokens utilisés
        }
    
    except requests.exceptions.Timeout:
        logger.error(f"Timeout après {REQUEST_TIMEOUT} secondes")
        return {
            "success": False,
            "content": None,
            "error": f"Délai d'attente dépassé ({REQUEST_TIMEOUT}s)"
        }
    
    except requests.exceptions.ConnectionError:
        logger.error("Erreur de connexion réseau")
        return {
            "success": False,
            "content": None,
            "error": "Impossible de se connecter à l'API Mistral"
        }
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur requête: {e}")
        return {
            "success": False,
            "content": None,
            "error": f"Erreur réseau: {str(e)}"
        }
    
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        return {
            "success": False,
            "content": None,
            "error": f"Erreur inattendue: {str(e)}"
        }

# ---------------------------------------------------------
# Exemple d'utilisation
# ---------------------------------------------------------
if __name__ == "__main__":
    # Test de l'API
    result = appel_mistral(
        prompt="Explique-moi la comptabilité en 2 phrases",
        temperature=0.3
    )
    
    if result["success"]:
        print(f"✅ Réponse: {result['content']}")
        print(f"📊 Tokens utilisés: {result.get('usage', {})}")
    else:
        print(f"❌ Erreur: {result['error']}")