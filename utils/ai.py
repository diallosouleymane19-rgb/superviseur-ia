"""
utils/ai.py - Client API Mistral optimisé pour Superviseur IA PCG
"""
import os
import time
import socket
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("superviseur_ia")

# =============================================================================
# CONFIGURATION API
# =============================================================================

API_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL_PRINCIPAL = "mistral-large-latest"
MODEL_FALLBACK = "mistral-medium-latest"  # Plus rapide, moins cher

# Timeouts critiques (connexion courte, lecture moderee)
CONNECT_TIMEOUT = 8.0      # 8s max pour etablir la connexion
READ_TIMEOUT = 45.0        # 45s max pour recevoir la reponse
MAX_RETRIES = 2            # 2 retries max (pas 3)
RETRY_DELAY = 2.0          # Delai initial court
RETRY_BACKOFF = 2.0        # Facteur de backoff

# =============================================================================
# RATE LIMITING PAR SESSION (protection couts API)
# =============================================================================
# Limites par plan (appels Mistral/jour par utilisateur)
RATE_LIMITS = {
    "free":       10,   # 10 appels/jour
    "starter":    50,   # 50 appels/jour
    "pro":       200,   # 200 appels/jour
    "enterprise": -1,   # illimite
    "demo":       5,    # 5 appels/jour
    "admin":     -1,    # illimite
}


def _get_rate_key() -> str:
    """Cle de rate limiting pour la session courante (email + jour)."""
    from datetime import date
    email = st.session_state.get("user_email", "anonymous")
    return f"_rl_{email}_{date.today().isoformat()}"


def check_rate_limit() -> tuple:
    """
    Verifie si l'utilisateur a atteint sa limite d'appels Mistral/jour.
    Retourne (autorise: bool, message: str, calls_today: int, limit: int)
    """
    plan  = st.session_state.get("plan", "free")
    limit = RATE_LIMITS.get(plan, RATE_LIMITS["free"])
    key   = _get_rate_key()

    if limit == -1:
        return True, "", 0, -1

    calls = st.session_state.get(key, 0)
    if calls >= limit:
        msg = (
            f"Limite d'analyses atteinte ({calls}/{limit} aujourd'hui). "
            f"Votre plan **{plan.capitalize()}** est limite a {limit} appels/jour. "
            "Passez au plan superieur pour continuer."
        )
        return False, msg, calls, limit
    return True, "", calls, limit


def increment_rate_counter():
    """Incremente le compteur d'appels Mistral pour la session."""
    key = _get_rate_key()
    st.session_state[key] = st.session_state.get(key, 0) + 1

# =============================================================================
# SESSION HTTP RÉUTILISABLE (Keep-Alive)
# =============================================================================

def get_session():
    """Crée ou récupère une session HTTP avec keep-alive et retry intelligent"""
    if 'http_session' not in st.session_state:
        session = requests.Session()
        
        # Retry UNIQUEMENT sur les erreurs réseau/connexion, PAS sur les timeouts de lecture
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=RETRY_DELAY,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=5,
            pool_maxsize=10
        )
        
        session.mount("https://", adapter)
        session.headers.update({
            "Connection": "keep-alive",
            "Accept-Encoding": "gzip, deflate"
        })
        
        st.session_state.http_session = session
        logger.info("Session HTTP créée avec keep-alive")
    
    return st.session_state.http_session

# =============================================================================
# UTILITAIRES RÉSEAU
# =============================================================================

def test_dns_resolution():
    """Test rapide si api.mistral.ai est joignable (< 2s)"""
    try:
        socket.getaddrinfo("api.mistral.ai", None, socket.AF_INET, socket.SOCK_STREAM)
        return True
    except Exception as e:
        logger.warning(f"DNS resolution failed: {e}")
        return False

def get_api_key():
    """Récupère la clé API de manière sécurisée"""
    key = st.secrets.get("MISTRAL_API_KEY") or os.getenv("MISTRAL_API_KEY")
    if not key:
        raise ValueError("❌ Clé MISTRAL_API_KEY manquante dans Settings > Secrets ou .env")
    return key

# =============================================================================
# APPEL API MISTRAL - VERSION CORRIGÉE
# =============================================================================

def appel_mistral(prompt, temperature=0.3, max_tokens=2000, use_fallback=False):
    """
    Appel API Mistral avec gestion robuste des timeouts et retry intelligent.
    
    Args:
        prompt: Le prompt complet à envoyer
        temperature: Température de génération (0.0 - 1.0)
        max_tokens: Limite de tokens pour réponse rapide
        use_fallback: Utiliser le modèle fallback (plus rapide)
    
    Returns:
        dict: {"success": bool, "content": str, "error": str}
    """
    # --- Rate limiting par session ---
    allowed, rl_msg, calls_today, rl_limit = check_rate_limit()
    if not allowed:
        return {"success": False, "content": "", "error": rl_msg}

    # Test DNS rapide avant toute tentative
    if not test_dns_resolution():
        return {
            "success": False,
            "content": "",
            "error": "🌐 Impossible de contacter api.mistral.ai - Vérifiez votre connexion internet"
        }
    
    api_key = get_api_key()
    model = MODEL_FALLBACK if use_fallback else MODEL_PRINCIPAL
    session = get_session()
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    last_error = None
    
    for attempt in range(MAX_RETRIES + 1):  # +1 pour tentative initiale
        try:
            logger.info(f"Appel API Mistral (tentative {attempt+1}/{MAX_RETRIES+1}, modèle: {model})")
            
            # ⏱ Timeout explicite : connexion courte, lecture modérée
            response = session.post(
                API_URL,
                headers=headers,
                json=payload,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
            )
            
            # Gestion des codes HTTP
            if response.status_code == 401:
                return {"success": False, "content": "", "error": "🔑 Clé API invalide"}
            elif response.status_code == 429:
                return {"success": False, "content": "", "error": "⏱ Rate limit atteint - patientez quelques minutes"}
            elif response.status_code >= 500:
                return {"success": False, "content": "", "error": f"🔥 Erreur serveur Mistral ({response.status_code})"}
            
            response.raise_for_status()
            data = response.json()
            
            if not data.get("choices"):
                return {"success": False, "content": "", "error": "Réponse API vide"}
            
            content = data["choices"][0].get("message", {}).get("content", "")
            
            logger.info(f"✅ Réponse reçue: {len(content)} caractères")
            increment_rate_counter()
            return {"success": True, "content": content, "error": ""}
            
        except requests.exceptions.ConnectTimeout:
            last_error = f"Timeout connexion ({CONNECT_TIMEOUT}s)"
            wait = RETRY_DELAY * (RETRY_BACKOFF ** attempt)
            logger.warning(f"Connect timeout, retry dans {wait:.1f}s")
            if attempt < MAX_RETRIES:
                time.sleep(wait)
                
        except requests.exceptions.ReadTimeout:
            last_error = f"Timeout lecture ({READ_TIMEOUT}s) - réponse trop lente"
            # PAS de retry sur read timeout → essayer fallback directement
            if not use_fallback:
                logger.info("🔄 Bascule vers modèle fallback...")
                return appel_mistral(prompt, temperature, max_tokens, use_fallback=True)
            return {"success": False, "content": "", "error": f"⏱ {last_error}\n\nL'API est surchargée. Réessayez dans 1-2 minutes."}
            
        except requests.exceptions.ConnectionError as e:
            last_error = f"Erreur connexion: {str(e)[:100]}"
            wait = RETRY_DELAY * (RETRY_BACKOFF ** attempt)
            logger.warning(f"Connection error, retry dans {wait:.1f}s")
            if attempt < MAX_RETRIES:
                time.sleep(wait)
                
        except requests.exceptions.RequestException as e:
            last_error = f"Erreur réseau: {str(e)[:100]}"
            break  # Pas de retry sur erreurs de requête génériques
            
        except Exception as e:
            last_error = f"Erreur inattendue: {str(e)[:100]}"
            logger.error(f"Erreur critique: {e}", exc_info=True)
            break
    
    # Si échec avec modèle principal, essayer fallback
    if not use_fallback:
        logger.info("🔄 Tentative avec modèle fallback après échec...")
        return appel_mistral(prompt, temperature, max_tokens, use_fallback=True)
    
    return {
        "success": False,
        "content": "",
        "error": (
            f"❌ Échec après {MAX_RETRIES} tentatives.\n\n"
            f"**Dernier problème:** {last_error}\n\n"
            f"**Solutions:**\n"
            f"• Vérifiez votre connexion internet\n"
            f"• Réessayez dans 1-2 minutes\n"
            f"• Si le problème persiste, contactez contact@smdconsulting.pro"
        )
    }

# =============================================================================
# FONCTIONS EXISTANTES (conservées pour compatibilité)
# =============================================================================

def extraire_contenu_mistral(contenu):
    """Extrait le contenu texte d'une réponse Mistral"""
    if isinstance(contenu, dict) and "content" in contenu:
        return contenu["content"]
    return str(contenu)

def appel_mistral_vision(image_data, prompt, temperature=0.3):
    """
    Appel API Mistral Vision pour analyse d'image (OCR).
    Même logique de timeout que appel_mistral.
    """
    # Réutilise la même session et logique
    return appel_mistral(
        prompt=f"[IMAGE ANALYSIS]\n{prompt}\n\nImage data: {image_data[:100]}...",
        temperature=temperature,
        max_tokens=4000  # Vision nécessite plus de tokens
    )
