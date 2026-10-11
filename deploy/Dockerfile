# Superviseur IA Comptable — image de l'application (hébergement OVH, France)
FROM python:3.11-slim

# OCR (pièces scannées), polices des graphiques, fuseau horaire de Paris
RUN apt-get update \
 && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-fra fonts-dejavu-core tzdata curl \
 && rm -rf /var/lib/apt/lists/*

ENV TZ=Europe/Paris \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# L'application ne tourne pas en administrateur
RUN useradd --create-home --uid 1000 smd && chown -R smd /app
USER smd

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
