import base64
from utils.ai import appel_mistral, extraire_contenu_mistral

def ocr_image_mistral(fichier):
    """
    OCR robuste via Mistral.
    - Support PDF / JPG / PNG
    - Pas d'appel à l'API Files (évite les erreurs d'ID)
    - Retourne toujours un texte ou un message d'erreur clair
    """

    # Détection du type MIME
    mime = fichier.type

    # Lecture du fichier en bytes
    bytes_data = fichier.read()

    # Encodage base64
    base64_data = base64.b64encode(bytes_data).decode()

    # Construction du message pour Mistral
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Extrais TOUT le texte de ce document."},
                {
                    "type": "input_image",
                    "image_url": f"data:{mime};base64,{base64_data}"
                }
            ]
        }
    ]

    # Appel Mistral
    try:
        result = appel_mistral(messages)
        texte = extraire_contenu_mistral(result).strip()

        if not texte:
            return "⚠️ OCR effectué mais aucun texte détecté."

        return texte

    except Exception as e:
        return f"❌ Erreur OCR : {str(e)}"
