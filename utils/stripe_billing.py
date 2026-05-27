# -*- coding: utf-8 -*-
"""
utils/stripe_billing.py — SMD Consulting
Intégration Stripe Billing : checkout, customer portal, webhooks.
Compatible PCG France & SYSCOHADA (mode test par défaut).
"""

import os
import stripe
from datetime import datetime


# ─── Configuration ────────────────────────────────────────────────────────────

def _get_stripe_key() -> str:
    """Récupère la clé Stripe depuis st.secrets ou variable d'environnement."""
    try:
        import streamlit as st
        key = st.secrets.get("STRIPE_SECRET_KEY", "")
        if key:
            return key
    except Exception:
        pass
    return os.getenv("STRIPE_SECRET_KEY", "")


def _get_webhook_secret() -> str:
    try:
        import streamlit as st
        return st.secrets.get("STRIPE_WEBHOOK_SECRET", "")
    except Exception:
        pass
    return os.getenv("STRIPE_WEBHOOK_SECRET", "")


def _get_app_url() -> str:
    try:
        import streamlit as st
        return st.secrets.get("APP_URL", "http://localhost:8501")
    except Exception:
        pass
    return os.getenv("APP_URL", "http://localhost:8501")


def _init_stripe():
    key = _get_stripe_key()
    if not key:
        raise RuntimeError(
            "Clé Stripe manquante. Ajoutez STRIPE_SECRET_KEY dans .streamlit/secrets.toml"
        )
    stripe.api_key = key


# ─── Catalogue des plans (Price IDs Stripe) ──────────────────────────────────
# Ces IDs sont à remplacer par vos vrais Price IDs créés dans le Dashboard Stripe.
# En mode test, créez les produits sur https://dashboard.stripe.com/test/products

STRIPE_PRICES = {
    # PCG France
    "pcg": {
        "starter":    {"monthly": "price_pcg_starter_monthly",    "annual": "price_pcg_starter_annual"},
        "pro":        {"monthly": "price_pcg_pro_monthly",        "annual": "price_pcg_pro_annual"},
        "enterprise": {"monthly": "price_pcg_enterprise_monthly", "annual": "price_pcg_enterprise_annual"},
    },
    # SYSCOHADA
    "syscohada": {
        "starter":    {"monthly": "price_sysc_starter_monthly",    "annual": "price_sysc_starter_annual"},
        "pro":        {"monthly": "price_sysc_pro_monthly",        "annual": "price_sysc_pro_annual"},
        "enterprise": {"monthly": "price_sysc_enterprise_monthly", "annual": "price_sysc_enterprise_annual"},
    },
    # Pack multi-agents (les deux apps)
    "multi": {
        "starter":    {"monthly": "price_multi_starter_monthly",    "annual": "price_multi_starter_annual"},
        "pro":        {"monthly": "price_multi_pro_monthly",        "annual": "price_multi_pro_annual"},
        "enterprise": {"monthly": "price_multi_enterprise_monthly", "annual": "price_multi_enterprise_annual"},
    },
}

# Tarifs en centimes EUR
PRICING = {
    "starter":    {"monthly": 2900,  "annual": 27900,  "label": "Starter",    "quota": 50},
    "pro":        {"monthly": 7900,  "annual": 75900,  "label": "Pro",        "quota": 200},
    "enterprise": {"monthly": 19900, "annual": 190900, "label": "Entreprise", "quota": -1},
}


# ─── Customer ─────────────────────────────────────────────────────────────────

def get_or_create_customer(email: str, nom: str = "", app: str = "pcg") -> str:
    """
    Retourne l'ID Stripe d'un customer existant ou en crée un nouveau.
    Synchronise avec la base RBAC.
    """
    _init_stripe()

    # Vérifier si déjà dans la DB RBAC
    try:
        from utils.auth_rbac import get_user, mettre_a_jour_stripe
        user = get_user(email)
        if user and user.get("stripe_customer_id"):
            return user["stripe_customer_id"]
    except Exception:
        pass

    # Chercher dans Stripe
    existing = stripe.Customer.list(email=email, limit=1)
    if existing.data:
        customer_id = existing.data[0].id
    else:
        # Créer le customer
        customer = stripe.Customer.create(
            email=email,
            name=nom or email,
            metadata={"app": app, "source": "smd_consulting"}
        )
        customer_id = customer.id

    # Sauvegarder dans RBAC
    try:
        mettre_a_jour_stripe(email, customer_id, "")
    except Exception:
        pass

    return customer_id


# ─── Checkout Session ─────────────────────────────────────────────────────────

def creer_checkout_session(
    email: str,
    plan: str,
    app: str = "pcg",
    billing: str = "monthly",
    nom: str = "",
) -> str:
    """
    Crée une session Stripe Checkout.
    Retourne l'URL de paiement à ouvrir dans le navigateur.
    """
    _init_stripe()

    if plan not in STRIPE_PRICES.get(app, {}):
        raise ValueError(f"Plan '{plan}' non disponible pour l'app '{app}'")

    price_id  = STRIPE_PRICES[app][plan][billing]
    app_url   = _get_app_url()
    customer_id = get_or_create_customer(email, nom, app)

    session = stripe.checkout.Session.create(
        customer          = customer_id,
        payment_method_types = ["card"],
        mode              = "subscription",
        line_items        = [{"price": price_id, "quantity": 1}],
        success_url       = f"{app_url}?stripe=success&plan={plan}&app={app}",
        cancel_url        = f"{app_url}?stripe=cancel",
        metadata          = {
            "email": email,
            "plan":  plan,
            "app":   app,
        },
        subscription_data = {
            "metadata": {
                "email": email,
                "plan":  plan,
                "app":   app,
            }
        },
        allow_promotion_codes = True,
    )
    return session.url


# ─── Customer Portal ──────────────────────────────────────────────────────────

def creer_portal_session(email: str, app: str = "pcg") -> str:
    """
    Crée une session Customer Portal Stripe pour gérer l'abonnement.
    Retourne l'URL du portail.
    """
    _init_stripe()
    app_url     = _get_app_url()
    customer_id = get_or_create_customer(email, app=app)

    session = stripe.billing_portal.Session.create(
        customer   = customer_id,
        return_url = f"{app_url}?stripe=portal_return",
    )
    return session.url


# ─── Webhook Handler ──────────────────────────────────────────────────────────

def traiter_webhook(payload: bytes, sig_header: str) -> dict:
    """
    Valide et traite un événement webhook Stripe.
    Retourne {"ok": True, "event": type} ou {"error": "..."}.
    """
    _init_stripe()
    webhook_secret = _get_webhook_secret()

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        return {"error": "Signature webhook invalide"}
    except Exception as e:
        return {"error": str(e)}

    event_type = event["type"]

    # ── Abonnement créé ou activé ─────────────────────────────────────────────
    if event_type in ("customer.subscription.created", "customer.subscription.updated"):
        sub  = event["data"]["object"]
        meta = sub.get("metadata", {})
        email = meta.get("email", "")
        plan  = meta.get("plan", "starter")
        app   = meta.get("app", "pcg")
        sub_id = sub["id"]
        status = sub.get("status", "")

        if email and status in ("active", "trialing"):
            try:
                from utils.auth_rbac import mettre_a_jour_plan, mettre_a_jour_stripe, log_action
                mettre_a_jour_plan(email, plan)
                mettre_a_jour_stripe(email, sub.get("customer", ""), sub_id)
                log_action(email, f"plan_upgraded:{plan}", app=app)
            except Exception as e:
                return {"error": f"Erreur mise à jour plan: {e}"}

    # ── Abonnement annulé ou suspendu ─────────────────────────────────────────
    elif event_type in ("customer.subscription.deleted",):
        sub   = event["data"]["object"]
        meta  = sub.get("metadata", {})
        email = meta.get("email", "")
        app   = meta.get("app", "pcg")

        if email:
            try:
                from utils.auth_rbac import mettre_a_jour_plan, log_action
                mettre_a_jour_plan(email, "free")
                log_action(email, "plan_cancelled:free", app=app)
            except Exception as e:
                return {"error": f"Erreur rétrogradation plan: {e}"}

    # ── Paiement échoué ───────────────────────────────────────────────────────
    elif event_type == "invoice.payment_failed":
        invoice = event["data"]["object"]
        customer_id = invoice.get("customer", "")
        # On pourrait envoyer un email ici via SendGrid/Resend
        pass

    return {"ok": True, "event": event_type}


# ─── Abonnement actuel ────────────────────────────────────────────────────────

def get_abonnement_actuel(email: str) -> dict | None:
    """
    Retourne les infos de l'abonnement Stripe actif d'un utilisateur.
    Retourne None si pas d'abonnement actif.
    """
    _init_stripe()
    try:
        from utils.auth_rbac import get_user
        user = get_user(email)
        if not user or not user.get("stripe_customer_id"):
            return None

        subs = stripe.Subscription.list(
            customer=user["stripe_customer_id"],
            status="active",
            limit=1
        )
        if not subs.data:
            return None

        sub   = subs.data[0]
        item  = sub["items"]["data"][0]
        price = item["price"]

        return {
            "subscription_id": sub["id"],
            "status":          sub["status"],
            "plan":            sub["metadata"].get("plan", "unknown"),
            "amount":          price["unit_amount"],
            "currency":        price["currency"],
            "interval":        price["recurring"]["interval"],
            "current_period_end": datetime.fromtimestamp(
                sub["current_period_end"]
            ).strftime("%d/%m/%Y"),
            "cancel_at_period_end": sub.get("cancel_at_period_end", False),
        }
    except Exception:
        return None


# ─── Streamlit : gestion retour Stripe ───────────────────────────────────────

def gerer_retour_stripe() -> None:
    """
    À appeler en haut du app.py principal pour intercepter les retours Stripe.
    Affiche un message de succès ou d'annulation.
    """
    try:
        import streamlit as st
        params = st.query_params

        if params.get("stripe") == "success":
            plan = params.get("plan", "")
            st.success(f"✅ Abonnement **{plan.capitalize()}** activé ! Bienvenue dans la plateforme SMD.")
            st.balloons()
            # Nettoyer les query params
            st.query_params.clear()

        elif params.get("stripe") == "cancel":
            st.info("ℹ️ Paiement annulé. Vous restez sur votre plan actuel.")
            st.query_params.clear()

        elif params.get("stripe") == "portal_return":
            st.success("✅ Votre abonnement a été mis à jour.")
            st.query_params.clear()

    except Exception:
        pass
