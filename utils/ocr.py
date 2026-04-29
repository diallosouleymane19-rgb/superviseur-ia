import requests
import os

API_KEY = os.getenv("MISTRAL_API_KEY")
MODEL = "mistral-large-latest"


def ocr_image_mistral(uploaded_file):
    url = "https://api.mistral.ai/v1/files"

    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }

    files = {
        "file": (uploaded_file.name, uploaded_file.getvalue())
    }

    response = requests.post(url, headers=headers, files=files)
    file_id = response.json()["id"]

    # Extraction du texte
    url_extract = "https://api.mistral.ai/v1/chat/completions"

    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Tu es un moteur OCR."},
            {"role": "user", "content": f"Extract text from file {file_id}"}
        ]
    }

    response = requests.post(url_extract, headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}, json=data)
    return response.json()["choices"][0]["message"]["content"]

