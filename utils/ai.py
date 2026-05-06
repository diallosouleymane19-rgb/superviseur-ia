import mistralai
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
import os

def appel_mistral(prompt):
    """Envoie une requête à l'IA Mistral et récupère la réponse brute"""
    api_key = os.getenv("MISTRAL_API_KEY")
    client = MistralClient(api_key=api_key)
    
    messages = [ChatMessage(role="user", content=prompt)]
    
    # On récupère la réponse de l'IA
    return client.chat(model="mistral-medium", messages=messages)

def extraire_contenu_mistral(reponse_brute):
    """
    FILTRE DE NETTOYAGE : 
    Extrait proprement uniquement le texte pour éviter l'affichage de codes techniques JSON.
    """
    try:
        # Si c'est l'objet standard de l'API Mistral
        if hasattr(reponse_brute, 'choices'):
            return reponse_brute.choices[0].message.content
        
        # Si c'est déjà une chaîne de caractères (du texte)
        elif isinstance(reponse_brute, str):
            return reponse_brute
            
        # Si c'est un dictionnaire technique (souvent la cause du rendu 'sale')
        elif isinstance(reponse_brute, dict):
            return reponse_brute.get('choices', [{}])[0].get('message', {}).get('content', "Contenu indisponible")
            
        return str(reponse_brute)
    except Exception:
        return "Désolé, une erreur est survenue lors de l'extraction de l'analyse."
