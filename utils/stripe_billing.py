# -*- coding: utf-8 -*-
"""
utils/stripe_billing.py — SMD Global Consulting LLC
Intégration Stripe Billing : checkout, customer portal, webhooks.
Superviseur IA PCG France (mode test par défaut).
"""

import json
import os
import stripe
from datetime import datetime


def _d(obj):
    """Objet Stripe -> dict Python (depuis stripe-python 13, un StripeObject n'est plus un dict)."""
    return obj.to_dict() if hasattr(obj, "to_dict") else (obj or {})


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


def paiement_actif() -> bool:
    """Vrai si une vraie clé Stripe est configurée (pas un modèle du type « sk_test_..._ICI »)."""
    key = _get_stripe_key().strip()
    if not key.startswith(("sk_test_", "sk_live_", "rk_test_", "rk_live_")) or len(key) < 30:
        return False
    return not any(m in key.upper() for m in ("ICI", "VOTRE", "XXXX", "..."))


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


# ─── Catalogue des plans ──────────────────────────────────────────────────────
# Les prix Stripe sont retrouvés par leur « lookup key » (ex. pcg_pro_monthly) : aucun identifiant
# à recopier. Ils sont créés par scripts/stripe_initialiser.py (mode test puis mode réel).

# Tarifs en centimes EUR
PRICING = {
    "starter":    {"monthly": 2900,  "annual": 27900,  "label": "Starter",    "quota": 50},
    "pro":        {"monthly": 7900,  "annual": 75900,  "label": "Pro",        "quota": 200},
    "enterprise": {"monthly": 19900, "annual": 190900, "label": "Entreprise", "quota": -1},
}


def cle_prix(app: str, plan: str, billing: str) -> str:
    return f"{app}_{plan}_{billing}"


def plan_depuis_cle(cle: str):
    """'pcg_pro_annual' -> 'pro' ; None si la clé n'est pas une des nôtres."""
    parties = (cle or "").split("_")
    return parties[1] if len(parties) == 3 and parties[1] in PRICING else None


def _price_id(app: str, plan: str, billing: str) -> str:
    cle = cle_prix(app, plan, billing)
    prix = stripe.Price.list(lookup_keys=[cle], active=True, limit=1).data
    if not prix:
        raise RuntimeError(f"Prix Stripe introuvable ({cle}) : lancez scripts/stripe_initialiser.py")
    return prix[0].id


def _plan_de_l_abonnement(sub) -> str:
    """Plan d'après le prix réellement souscrit (suit les changements faits dans le portail Stripe)."""
    try:
        for item in sub["items"]["data"]:
            plan = plan_depuis_cle(item["price"].get("lookup_key"))
            if plan:
                return plan
    except Exception:
        pass
    return (sub.get("metadata") or {}).get("plan", "starter")


def _email_de_l_abonnement(sub) -> str:
    email = (sub.get("metadata") or {}).get("email", "")
    if not email and sub.get("customer"):
        try:
            email = _d(stripe.Customer.retrieve(sub["customer"])).get("email") or ""
        except Exception:
            email = ""
    return email.lower().strip()


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

    if plan not in PRICING or billing not in ("monthly", "annual"):
        raise ValueError(f"Plan '{plan}' ou facturation '{billing}' inconnus")

    price_id  = _price_id(app, plan, billing)
    app_url   = _get_app_url()
    customer_id = get_or_create_customer(email, nom, app)

    session = stripe.checkout.Session.create(
        customer          = customer_id,
        # Facture B2B : adresse de facturation et n° de TVA intracommunautaire du client
        billing_address_collection = "required",
        tax_id_collection = {"enabled": True},
        customer_update   = {"name": "auto", "address": "auto"},
        mode              = "subscription",
        line_items        = [{"price": price_id, "quantity": 1}],
        success_url       = f"{app_url}/?stripe=success&plan={plan}&app={app}",
        cancel_url        = f"{app_url}/?stripe=cancel",
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

def _portal_config_id():
    """Configuration du portail créée par scripts/stripe_initialiser.py (évite l'erreur
    « default configuration has not been created » du mode test)."""
    try:
        for c in stripe.billing_portal.Configuration.list(active=True, limit=20).data:
            if _d(c).get("metadata", {}).get("app") == "kontrolia":
                return c.id
    except Exception:
        pass
    return None


def creer_portal_session(email: str, app: str = "pcg") -> str:
    """
    Crée une session Customer Portal Stripe pour gérer l'abonnement.
    Retourne l'URL du portail.
    """
    _init_stripe()
    app_url     = _get_app_url()
    customer_id = get_or_create_customer(email, app=app)

    params = dict(customer=customer_id, return_url=f"{app_url}/?stripe=portal_return")
    config = _portal_config_id()
    if config:
        params["configuration"] = config
    session = stripe.billing_portal.Session.create(**params)
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
        stripe.Webhook.construct_event(payload, sig_header, webhook_secret)   # vérifie la signature
        event = json.loads(payload)                                           # contenu en dict simple
    except stripe.error.SignatureVerificationError:
        return {"error": "Signature webhook invalide"}
    except Exception as e:
        return {"error": str(e)}

    event_type = event["type"]

    # ── Abonnement créé, modifié (changement de plan dans le portail), suspendu ou annulé ──
    if event_type in ("customer.subscription.created", "customer.subscription.updated",
                      "customer.subscription.deleted"):
        sub    = event["data"]["object"]
        app    = (sub.get("metadata") or {}).get("app", "pcg")
        email  = _email_de_l_abonnement(sub)
        status = sub.get("status", "")
        if not email:
            return {"error": "Abonnement sans e-mail : impossible de retrouver le compte"}
        try:
            from utils.auth_rbac import mettre_a_jour_plan, mettre_a_jour_stripe, log_action
            if event_type != "customer.subscription.deleted" and status in ("active", "trialing"):
                plan = _plan_de_l_abonnement(sub)
                mettre_a_jour_plan(email, plan)
                mettre_a_jour_stripe(email, sub.get("customer", ""), sub["id"])
                log_action(email, "ABONNEMENT", details=f"Plan {plan} ({status})", app=app)
            elif event_type == "customer.subscription.deleted" or status in ("canceled", "unpaid",
                                                                              "incomplete_expired"):
                mettre_a_jour_plan(email, "free")
                log_action(email, "ABONNEMENT", details=f"Retour au plan Gratuit ({status or 'résilié'})", app=app)
            # past_due / incomplete : on attend la relance de paiement de Stripe, le plan est conservé
        except Exception as e:
            return {"error": f"Erreur mise à jour plan: {e}"}

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

        sub   = _d(subs.data[0])
        item  = sub["items"]["data"][0]
        price = item["price"]

        return {
            "subscription_id": sub["id"],
            "status":          sub["status"],
            "plan":            _plan_de_l_abonnement(sub),
            "amount":          price["unit_amount"],
            "currency":        price["currency"],
            "interval":        price["recurring"]["interval"],
            # Depuis l'API Stripe 2025, la fin de période est portée par la ligne d'abonnement
            "current_period_end": datetime.fromtimestamp(
                sub.get("current_period_end") or item.get("current_period_end")
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
            st.success(f"Abonnement **{plan.capitalize()}** activé ! Bienvenue dans la plateforme SMD.", icon=":material/check_circle:")
            st.balloons()
            # Nettoyer les query params
            st.query_params.clear()

        elif params.get("stripe") == "cancel":
            st.info("Paiement annulé. Vous restez sur votre plan actuel.", icon=":material/info:")
            st.query_params.clear()

        elif params.get("stripe") == "portal_return":
            st.success("Votre abonnement a été mis à jour.", icon=":material/check_circle:")
            st.query_params.clear()

    except Exception:
        pass
