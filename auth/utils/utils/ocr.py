import base64
from .ai import appel_mistral, extraire_contenu_mistral

def ocr_image_mistral(bytes_data: bytes, mime: str) -> str:
    """
    Effectue l'OCR d'une image via Mistral AI.
    Retourne le texte extrait.
    """
    base64_data = base64.b64encode(bytes_data).decode()

    result = appel_mistral([
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Extrais le texte de cette image."},
                {"type": "input_image", "image_url": f"data:{mime};base64,{base64_data}"}
            ]
        }
    ])

    texte = extraire_contenu_mistral(result).strip()
    return texte

