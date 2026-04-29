import base64
import tempfile
from pdf2image import convert_from_bytes
from .ai import appel_mistral, extraire_contenu_mistral


def _pdf_to_images(pdf_bytes):
    """
    Convertit un PDF en liste d'images PIL.
    Supporte les PDF multi-pages.
    """
    try:
        images = convert_from_bytes(pdf_bytes)
        return images
    except Exception as e:
        return None


def _pil_image_to_base64(img):
    """
    Convertit une image PIL en base64 PNG.
    """
    with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
        img.save(tmp.name, format="PNG")
        with open(tmp.name, "rb") as f:
            return base64.b64encode(f.read()).decode()


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


def ocr_image_mistral(uploaded_file):
    """
    OCR complet :
    - PDF multi-pages → images
    - Images → base64 → Mistral
    - Concaténation du texte
    """

    filename = uploaded_file.name.lower()
    file_bytes = uploaded_file.read()

    # ---------------------------------------------------------
    # CAS 1 : PDF → conversion en images
    # ---------------------------------------------------------
    if filename.endswith(".pdf"):
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
    # CAS 2 : Image directe (PNG, JPG…)
    # ---------------------------------------------------------
    else:
        mime = "image/png"
        if filename.endswith(".jpg") or filename.endswith(".jpeg"):
            mime = "image/jpeg"

        base64_data = base64.b64encode(file_bytes).decode()
        return _ocr_image_base64(base64_data, mime=mime)
