import base64
import tempfile
from io import BytesIO
from pdf2image import convert_from_bytes
from PyPDF2 import PdfReader
from .ai import appel_mistral, extraire_contenu_mistral

# ---------------------------------------------------------
# 1) Limitation de taille (5 Mo)
# ---------------------------------------------------------
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 Mo

def _taille_valide(file_bytes):
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        return False
    return True

# ---------------------------------------------------------
# 2) Extraction directe du texte (PDF texte)
# ---------------------------------------------------------
def _extract_pdf_text(pdf_bytes):
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        texte = ""
        for page in reader.pages:
            contenu = page.extract_text() or ""
            texte += contenu + "\n"
        texte = texte.strip()
        if len(texte) > 10:
            return texte
        return None
    except Exception:
        return None

# ---------------------------------------------------------
# 3) Conversion PDF → images
# ---------------------------------------------------------
def _pdf_to_images(pdf_bytes):
    try:
        images = convert_from_bytes(pdf_bytes)
        return images
    except Exception:
        return None

# ---------------------------------------------------------
# 4) PIL → base64
# ---------------------------------------------------------
def _pil_image_to_base64(img):
    try:
        with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
            img.save(tmp.name, format="PNG")
            with open(tmp.name, "rb") as f:
                return base64.b64encode(f.read()).decode()
    except Exception:
        return None

# ---------------------------------------------------------
# 5) OCR via Mistral (Pixtral-Vision)
# ---------------------------------------------------------
def _ocr_image_base64(base64_data, mime="image/png"):
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Extrais tout le texte de cette image."},
                {"type": "input_image", "image_url": f"data:{mime};base64,{base64_data}"}
            ]
        }
    ]
    result = appel_mistral(messages)
    return extraire_contenu_mistral(result)

# ---------------------------------------------------------
# 6) Fonction principale (OCR)
# ---------------------------------------------------------
def ocr_image_mistral(uploaded_file):
    """
    OCR complet :
    - PDF texte → extraction directe
    - PDF image → conversion en images + OCR
    - PNG/JPG → OCR direct
    """
    filename = uploaded_file.name.lower()
    file_bytes = uploaded_file.read()

    # Vérification de la taille
    if not _taille_valide(file_bytes):
        return "❌ Fichier trop volumineux (limite 5 Mo). Veuillez compresser l'image ou le PDF."

    # -------------------------------------------------
    # Cas PDF
    # -------------------------------------------------
    if filename.endswith(".pdf"):
        # Essai extraction directe
        texte = _extract_pdf_text(file_bytes)
        if texte:
            return texte

        # Sinon : conversion en images
        images = _pdf_to_images(file_bytes)
        if images is None:
            return "❌ Erreur : impossible de convertir le PDF en images."

        texte_total = ""
        for i, img in enumerate(images):
            base64_img = _pil_image_to_base64(img)
            if base64_img is None:
                texte_total += f"\n\n--- Page {i+1} ---\n⚠️ Conversion échouée"
                continue
            texte_page = _ocr_image_base64(base64_img)
            texte_total += f"\n\n--- Page {i+1} ---\n{texte_page}"

        return texte_total.strip()

    # -------------------------------------------------
    # Cas image directe (PNG, JPG, JPEG)
    # -------------------------------------------------
    else:
        mime = "image/png"
        if filename.endswith(".jpg") or filename.endswith(".jpeg"):
            mime = "image/jpeg"
        base64_data = base64.b64encode(file_bytes).decode()
        return _ocr_image_base64(base64_data, mime=mime)