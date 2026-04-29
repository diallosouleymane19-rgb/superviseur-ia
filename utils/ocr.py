import base64
import tempfile
from io import BytesIO
from pdf2image import convert_from_bytes
from PyPDF2 import PdfReader
from .ai import appel_mistral, extraire_contenu_mistral


# ---------------------------------------------------------
# 1) Extraction directe du texte (PDF texte)
# ---------------------------------------------------------
def _extract_pdf_text(pdf_bytes):
    """
    Extraction directe du texte pour les PDF vectoriels (Shopify, Stripe, Amazon, etc.)
    """
    try:
        reader = PdfReader(BytesIO(pdf_bytes))  # Correction essentielle
        texte = ""

        for page in reader.pages:
            contenu = page.extract_text() or ""
            texte += contenu + "\n"

        texte = texte.strip()

        # Si le PDF contient du texte réel
        if len(texte) > 10:
            return texte

        return None

    except Exception:
        return None


# ---------------------------------------------------------
# 2) Conversion PDF → images (PDF image)
# ---------------------------------------------------------
def _pdf_to_images(pdf_bytes):
    """
    Convertit un PDF image en liste d'images PIL.
    """
    try:
        images = convert_from_bytes(pdf_bytes)
        return images
    except Exception:
        return None


# ---------------------------------------------------------
# 3) Conversion PIL → base64
# ---------------------------------------------------------
def _pil_image_to_base64(img):
    """
    Convertit une image PIL en base64 PNG.
    """
    with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
        img.save(tmp.name, format="PNG")
        with open(tmp.name, "rb") as f:
            return base64.b64encode(f.read()).decode()


# ---------------------------------------------------------
# 4) OCR Mistral sur image base64
# ---------------------------------------------------------
def _ocr_image_base64(base64_data, mime="image/png"):
    """
    Envoie une image encodée en base64 à Mistral (Pixtral-Vision).
    """
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
# 5) OCR principal (PDF + images)
# ---------------------------------------------------------
def ocr_image_mistral(uploaded_file):
    """
    OCR complet :
    - PDF texte → extraction directe
    - PDF image → conversion + OCR
    - Images → OCR direct
    """
    filename = uploaded_file.name.lower()
    file_bytes = uploaded_file.read()

    # ---------------------------------------------------------
    # CAS A : PDF
    # ---------------------------------------------------------
    if filename.endswith(".pdf"):

        # 1) Essayer extraction directe (PDF texte)
        texte_pdf = _extract_pdf_text(file_bytes)
        if texte_pdf:
            return texte_pdf

        # 2) Sinon → conversion en images (PDF image)
        images = _pdf_to_images(file_bytes)
        if images is None:
            return "❌ Erreur : impossible de convertir le PDF en images."

        texte_total = ""

        for i, img in enumerate(images):
            base64_img = _pil_image_to_base64(img)
            texte_page = _ocr_image_base64(base64_img)

            texte_total += f"\n\n--- Page {i+1} ---\n{texte_page}"

        return texte_total.strip()

    # ---------------------------------------------------------
    # CAS B : Image directe (PNG, JPG, JPEG)
    # ---------------------------------------------------------
    else:
        mime = "image/png"
        if filename.endswith(".jpg") or filename.endswith(".jpeg"):
            mime = "image/jpeg"

        base64_data = base64.b64encode(file_bytes).decode()
        return _ocr_image_base64(base64_data, mime=mime)
