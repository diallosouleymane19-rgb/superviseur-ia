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


# Offre « Programme Cabinet Fondateur » (25 premiers clients) : Pro à 49,99 € HT/mois garanti, remise de 20 €
# les 3 premiers mois (29,99 € HT). Donne les droits du plan Pro ; absente du portail (pas de bascule vers ce prix).
FONDATEUR = {"plan": "fondateur", "droits": "pro", "monthly": 4999, "label": "Pro Fondateur",
             "coupon": "kontrolia_fondateur", "remise": 2000, "mois_remise": 3, "places": 25}
PLAN_DROITS = {FONDATEUR["plan"]: FONDATEUR["droits"]}


def cle_prix(app: str, plan: str, billing: str) -> str:
    return f"{app}_{plan}_{billing}"


def plan_depuis_cle(cle: str):
    """'pcg_pro_annual' -> 'pro' ; 'pcg_fondateur_monthly' -> 'pro' (droits) ; None si la clé n'est pas une des nôtres."""
    parties = (cle or "").split("_")
    if len(parties) == 3 and parties[1] in PRICING:
        return parties[1]
    if len(parties) == 3 and parties[1] in PLAN_DROITS:
        return PLAN_DROITS[parties[1]]
    return None


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


def abonnements_actifs(customer_id: str) -> list:
    """Abonnements actifs (ou en essai) d'un client Stripe, en dict."""
    if not customer_id:
        return []
    out = []
    for statut in ("active", "trialing", "past_due"):
        out += [_d(x) for x in stripe.Subscription.list(customer=customer_id, status=statut, limit=10).data]
    return out


RANG_PLAN = {"starter": 1, "pro": 2, "enterprise": 3}


def _meilleur_abonnement(customer_id: str, sub: dict) -> dict:
    """Abonnement actif au plan le plus élevé (celui de l'événement s'il n'y en a pas d'autre)."""
    try:
        tous = {x["id"]: x for x in abonnements_actifs(customer_id)}
    except Exception:
        tous = {}
    tous[sub["id"]] = sub
    return max(tous.values(), key=lambda x: RANG_PLAN.get(_plan_de_l_abonnement(x), 0))


def _autre_abonnement_actif(customer_id: str, sauf: str):
    try:
        return next((x for x in abonnements_actifs(customer_id) if x["id"] != sauf), None)
    except Exception:
        return None


def _email_de_l_abonnement(sub) -> str:
    email = (sub.get("metadata") or {}).get("email", "")
    if not email and sub.get("customer"):
        try:
            email = _d(stripe.Customer.retrieve(sub["customer"])).get("email") or ""
        except Exception:
            email = ""
    return email.lower().strip()


# Mentions de facture B2B (Code de commerce, art. L441-9, L441-10 et D441-5), en pied de chaque facture Stripe.
# Le n° de TVA et l'immatriculation du vendeur s'ajoutent dans les paramètres du compte Stripe.
MENTIONS_FACTURE = (
    "Nature : prestation de services.\n"
    "Conditions de paiement : à la réception de facture, par prélèvement sur le moyen de paiement enregistré. "
    "Pas d'escompte pour paiement anticipé.\n"
    "Retard de paiement : pénalités au taux de trois fois le taux d'intérêt légal et indemnité forfaitaire "
    "pour frais de recouvrement de 40 € (art. L441-10 et D441-5 du Code de commerce)."
)


MENTION_AUTOLIQUIDATION = ("TVA : autoliquidation, taxe due par le preneur (art. 283-2 du CGI). "
                           "Montants hors taxe ; prestataire établi hors de France.")


def regime_tva() -> str:
    """« autoliquidation » (défaut : vendeur établi hors de France, clients professionnels) ou « 20 »
    (TVA française ajoutée), d'après le secret STRIPE_TVA."""
    try:
        import streamlit as st
        v = str(st.secrets.get("STRIPE_TVA", "")).strip()
    except Exception:
        v = ""
    v = v or os.getenv("STRIPE_TVA", "").strip()
    return "20" if v == "20" else "autoliquidation"


def _bloc_vendeur(vendeur: str) -> str:
    """Identité du vendeur, une information par ligne (le secret sépare les éléments par « — »)."""
    return "\n".join(p.strip() for p in vendeur.split(" — ") if p.strip())


def _mentions_facture() -> str:
    """Pied de facture : identité du vendeur (secret STRIPE_MENTIONS_VENDEUR : siège, EIN…), ligne vide, mentions B2B."""
    try:
        import streamlit as st
        vendeur = str(st.secrets.get("STRIPE_MENTIONS_VENDEUR", "")).strip()
    except Exception:
        vendeur = os.getenv("STRIPE_MENTIONS_VENDEUR", "").strip()
    tva = (MENTION_AUTOLIQUIDATION + "\n") if regime_tva() == "autoliquidation" else ""
    return (_bloc_vendeur(vendeur) + "\n\n" if vendeur else "") + tva + MENTIONS_FACTURE


def _taux_tva_id():
    """Taux de TVA 20 % créé par scripts/stripe_initialiser.py ; None en autoliquidation ou s'il n'existe pas."""
    if regime_tva() == "autoliquidation":
        return None
    try:
        for t in stripe.TaxRate.list(active=True, limit=100).data:
            if _d(t).get("metadata", {}).get("app") == "kontrolia":
                return t.id
    except Exception:
        pass
    return None


class DejaAbonne(Exception):
    """Le client a déjà un abonnement actif : pas de second abonnement."""


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
            try:   # un client créé en mode test n'existe pas en mode réel (et inversement)
                c = stripe.Customer.retrieve(user["stripe_customer_id"])
                if not _d(c).get("deleted"):
                    return user["stripe_customer_id"]
            except stripe.error.InvalidRequestError:
                pass
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

    fondateur = plan == FONDATEUR["plan"]
    if fondateur:
        billing = "monthly"
    elif plan not in PRICING or billing not in ("monthly", "annual"):
        raise ValueError(f"Plan '{plan}' ou facturation '{billing}' inconnus")
    if fondateur and places_fondateur() <= 0:
        raise ValueError("Les 25 places du Programme Cabinet Fondateur sont prises.")

    app_url   = _get_app_url()
    customer_id = get_or_create_customer(email, nom, app)
    if abonnements_actifs(customer_id):
        # Un seul abonnement par cabinet : le changement de plan passe par le portail Stripe
        raise DejaAbonne("Un abonnement est déjà en cours : changez de plan depuis le portail Stripe.")
    price_id = _price_id(app, plan, billing)
    try:   # mentions légales en pied de facture (aussi pour les clients créés avant cette version)
        stripe.Customer.modify(customer_id, invoice_settings={"footer": _mentions_facture()},
                               preferred_locales=["fr-FR"])   # factures et reçus en français
    except Exception:
        pass
    taux = _taux_tva_id()

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
            **({"default_tax_rates": [taux]} if taux else {}),
            "metadata": {
                "email": email,
                "plan":  plan,
                "app":   app,
            }
        },
        # Remise fondateur appliquée d'office ; sinon codes promo possibles (Stripe refuse les deux à la fois)
        **({"discounts": [{"coupon": FONDATEUR["coupon"]}]} if fondateur else {"allow_promotion_codes": True}),
        locale            = "fr",
    )
    return session.url


def places_fondateur() -> int:
    """Places restantes du Programme Cabinet Fondateur (coupon limité à 25 utilisations) ; 0 si indisponible."""
    try:
        _init_stripe()
        c = _d(stripe.Coupon.retrieve(FONDATEUR["coupon"]))
        if not c.get("valid", False):
            return 0
        return max(0, (c.get("max_redemptions") or FONDATEUR["places"]) - (c.get("times_redeemed") or 0))
    except Exception:
        return 0


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

    params = dict(customer=customer_id, return_url=f"{app_url}/?stripe=portal_return", locale="fr")
    try:   # factures en français, y compris pour les clients créés avant cette version
        stripe.Customer.modify(customer_id, preferred_locales=["fr-FR"],
                               invoice_settings={"footer": _mentions_facture()})
    except Exception:
        pass
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
                # Plusieurs abonnements possibles (ancien en fin de période + nouveau) : le plus élevé s'applique
                meilleur = _meilleur_abonnement(sub.get("customer", ""), sub)
                plan = _plan_de_l_abonnement(meilleur)
                mettre_a_jour_plan(email, plan)
                mettre_a_jour_stripe(email, sub.get("customer", ""), meilleur["id"])
                fin = " ; résiliation en fin de période" if sub.get("cancel_at_period_end") else ""
                log_action(email, "ABONNEMENT", details=f"Plan {plan} ({status}{fin})", app=app)
            elif event_type == "customer.subscription.deleted" or status in ("canceled", "unpaid",
                                                                              "incomplete_expired"):
                autre = _autre_abonnement_actif(sub.get("customer", ""), sub["id"])
                if autre:   # un autre abonnement reste actif : c'est lui qui fixe le plan
                    plan = _plan_de_l_abonnement(autre)
                    mettre_a_jour_plan(email, plan)
                    mettre_a_jour_stripe(email, sub.get("customer", ""), autre["id"])
                    log_action(email, "ABONNEMENT", details=f"Abonnement résilié ; plan {plan} conservé", app=app)
                else:
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
            libelle = FONDATEUR["label"] if plan == FONDATEUR["plan"] else PRICING.get(plan, {}).get("label", plan.capitalize())
            st.success(f"Paiement accepté : abonnement **{libelle}** KontrolIA. "
                       + ("Il est actif sur votre compte." if st.session_state.get("authenticated")
                          else "Connectez-vous pour en profiter (activation en quelques secondes)."),
                       icon=":material/check_circle:")
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
