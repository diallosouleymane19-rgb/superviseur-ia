# -*- coding: utf-8 -*-
"""Module OCR Autonome - SMD Global Consulting LLC"""
import base64
import os
import io
import requests
from dotenv import load_dotenv

load_dotenv()

# Taille max image : 4 Mo
MAX_IMAGE_SIZE = 4 * 1024 * 1024

def pdf_to_image_bytes(file_bytes):
    """Convertit la première page d'un PDF en image PNG via PyMuPDF (sans Poppler)"""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page = doc[0]
        mat = fitz.Matrix(2.0, 2.0)  # zoom x2 pour meilleure qualité
        pix = page.get_pixmap(matrix=mat)
        buf = io.BytesIO(pix.tobytes("png"))
        return buf.getvalue(), None
    except ImportError:
        return None, "❌ PyMuPDF non installé. Lancez : pip install pymupdf"
    except Exception as e:
        return None, f"❌ Erreur conversion PDF : {e}"

def ocr_image_mistral(uploaded_file):
    """Extrait le texte d'une image/PDF via Mistral Vision (Pixtral)"""
    try:
        api_key = os.getenv('MISTRAL_API_KEY')
        if not api_key:
            return None, "❌ Clé API Mistral manquante dans le fichier .env"

        # Lire le fichier
        uploaded_file.seek(0)
        file_bytes = uploaded_file.read()
        nom = uploaded_file.name.lower()

        # --- Conversion PDF → image (PyMuPDF, sans Poppler) ---
        if nom.endswith('.pdf'):
            file_bytes, erreur = pdf_to_image_bytes(file_bytes)
            if erreur:
                return None, erreur
            media_type = "image/png"

        # --- Détection type image ---
        elif nom.endswith('.png'):
            media_type = "image/png"
        elif nom.endswith(('.jpg', '.jpeg')):
            media_type = "image/jpeg"
        else:
            media_type = "image/png"

        # --- Vérification taille ---
        if len(file_bytes) > MAX_IMAGE_SIZE:
            return None, f"❌ Fichier trop volumineux ({len(file_bytes) // 1024} Ko). Maximum : 4 Mo."

        # --- Encodage base64 ---
        image_base64 = base64.b64encode(file_bytes).decode('utf-8')

        # --- Appel API Mistral (Pixtral) ---
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "pixtral-12b-2409",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Tu es un assistant comptable expert. "
                                "Extrais tout le texte de ce document en respectant "
                                "la mise en forme originale (tableaux, montants, dates, "
                                "numéros de facture, TVA, totaux). "
                                "Retourne uniquement le texte extrait, sans commentaire."
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4000
        }

        response = requests.post(url, headers=headers, json=payload, timeout=60)

        if response.status_code == 200:
            data = response.json()
            texte = data['choices'][0]['message']['content']
            return texte, None
        else:
            return None, f"❌ Erreur API Mistral ({response.status_code}) : {response.text}"

    except requests.exceptions.Timeout:
        return None, "❌ Délai d'attente dépassé (60s). Réessayez avec un fichier plus léger."
    except Exception as e:
        return None, f"❌ Erreur inattendue : {e}"