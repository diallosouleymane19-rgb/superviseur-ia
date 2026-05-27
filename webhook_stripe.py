# -*- coding: utf-8 -*-
"""
webhook_stripe.py — SMD Consulting / Superviseur IA PCG France
Serveur FastAPI minimal pour recevoir les webhooks Stripe.

Lancement :
    pip install fastapi uvicorn
    uvicorn webhook_stripe:app --host 0.0.0.0 --port 4242

Expose publiquement (dev) avec ngrok :
    ngrok http 4242
    → copier l'URL ngrok dans Stripe Dashboard > Webhooks

Événements à abonner dans le Dashboard Stripe :
    customer.subscription.created
    customer.subscription.updated
    customer.subscription.deleted
    invoice.payment_failed
    invoice.payment_succeeded
"""

import os
import sys
import logging

# Ajouter le répertoire courant au path pour importer utils/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.responses import JSONResponse
except ImportError:
    raise ImportError("Installez FastAPI : pip install fastapi uvicorn")

from utils.stripe_billing import traiter_webhook

# ─── App ──────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SMD Consulting — Stripe Webhook",
    description="Récepteur d'événements Stripe pour la plateforme SMD",
    version="1.0.0",
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "smd-stripe-webhook"}


@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """
    Endpoint principal webhook Stripe.
    Stripe envoie tous les événements ici avec une signature HMAC.
    """
    payload    = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not sig_header:
        logger.warning("Requête sans signature Stripe rejetée")
        raise HTTPException(status_code=400, detail="Signature manquante")

    logger.info(f"Webhook reçu — {len(payload)} bytes")

    result = traiter_webhook(payload, sig_header)

    if "error" in result:
        logger.error(f"Erreur webhook: {result['error']}")
        raise HTTPException(status_code=400, detail=result["error"])

    logger.info(f"Webhook traité : {result.get('event', 'unknown')}")
    return JSONResponse({"received": True, "event": result.get("event")})


# ─── Lancement direct ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        import uvicorn
    except ImportError:
        raise ImportError("Installez uvicorn : pip install uvicorn")

    port = int(os.getenv("WEBHOOK_PORT", "4242"))
    logger.info(f"Démarrage webhook Stripe sur port {port}")
    logger.info("Configurez l'URL dans Stripe Dashboard > Webhooks")
    uvicorn.run("webhook_stripe:app", host="0.0.0.0", port=port, reload=False)
