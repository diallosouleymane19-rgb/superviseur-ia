# config/settings.py

import os
from dotenv import load_dotenv

# Charger automatiquement le fichier .env
load_dotenv()

# ============================
# 🔐 Clés API
# ============================

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# ============================
# 🤖 Modèles IA
# ============================

MODEL_TEXT = "mistral-large-latest"
MODEL_OCR = "pixtral-12b-2409"

# ============================
# 🌍 Environnement
# ============================

ENV = os.getenv("ENV", "dev")  # dev | prod

# ============================
# 📁 Chemins importants
# ============================

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DOSSIER_EXPORT = os.path.join(BASE_DIR, "exports")
DOSSIER_UPLOADS = os.path.join(BASE_DIR, "uploads")
DOSSIER_FEC = os.path.join(BASE_DIR, "uploads", "fec")
DOSSIER_BALANCES = os.path.join(BASE_DIR, "uploads", "balances")

# Création automatique des dossiers si absents
for dossier in [DOSSIER_EXPORT, DOSSIER_UPLOADS, DOSSIER_FEC, DOSSIER_BALANCES]:
    if not os.path.exists(dossier):
        os.makedirs(dossier)
