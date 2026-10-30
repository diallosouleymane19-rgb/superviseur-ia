# -*- coding: utf-8 -*-
"""
Prépare le compte Stripe de KontrolIA (à lancer une fois en mode test, puis une fois en mode réel) :
  1. produits et prix des plans Starter, Pro, Entreprise (mensuel et annuel), retrouvés par « lookup key » ;
  2. configuration du portail client (changer de plan, résilier, carte, factures) ;
  3. point de réception des événements (webhook) sur https://<APP_URL>/webhook/stripe.

Idempotent : ce qui existe déjà est réutilisé. Le webhook est recréé à chaque lancement, car Stripe ne
montre son secret qu'à la création.
Sortie standard : uniquement la ligne STRIPE_WEBHOOK_SECRET à ajouter à secrets.toml (rien d'autre).
Messages pour l'utilisateur : sur la sortie d'erreur.
Lancement (serveur) : sudo bash deploy/configurer_stripe.sh
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import stripe  # noqa: E402

from utils.stripe_billing import (PRICING, FONDATEUR, cle_prix, regime_tva, _d, _get_app_url,  # noqa: E402
                                  _get_stripe_key)

APP = "pcg"
EVENEMENTS = ["customer.subscription.created", "customer.subscription.updated",
              "customer.subscription.deleted", "invoice.payment_failed"]


def info(msg):
    print(msg, file=sys.stderr)


def produits_et_prix():
    prix_par_produit = {}
    for plan, p in PRICING.items():
        cles = {b: cle_prix(APP, plan, b) for b in ("monthly", "annual")}
        existants = {x.lookup_key: x for x in stripe.Price.list(lookup_keys=list(cles.values()), active=True).data}
        produit = None
        if existants:
            produit = next(iter(existants.values())).product
        else:
            produit = stripe.Product.create(name=f"KontrolIA {p['label']}",
                                            metadata={"app": "kontrolia", "plan": plan}).id
        ids = []
        for billing, cle in cles.items():
            if cle in existants:
                prix = existants[cle]
                if prix.unit_amount != p[billing]:
                    info(f"  ATTENTION : {cle} existe à {prix.unit_amount / 100:.2f} € au lieu de "
                         f"{p[billing] / 100:.2f} € (non modifié).")
            else:
                prix = stripe.Price.create(
                    product=produit, currency="eur", unit_amount=p[billing], lookup_key=cle,
                    recurring={"interval": "month" if billing == "monthly" else "year"},
                    nickname=f"{p['label']} {'mensuel' if billing == 'monthly' else 'annuel'}")
                info(f"  Prix créé : {cle} = {p[billing] / 100:.2f} €")
            ids.append(prix.id)
        prix_par_produit[produit] = ids
    info(f"1/3 Produits et prix prêts ({len(prix_par_produit)} plans payants).")
    return prix_par_produit


def offre_fondateur():
    """Prix Pro Fondateur 49,99 € HT/mois + coupon de 20 € pendant 3 mois, limité à 25 clients.
    Pas ajouté au portail client : on n'y bascule pas depuis un autre plan."""
    cle = cle_prix(APP, FONDATEUR["plan"], "monthly")
    existant = stripe.Price.list(lookup_keys=[cle], active=True, limit=1).data
    if existant:
        info(f"  Prix fondateur déjà présent : {existant[0].unit_amount / 100:.2f} €")
    else:
        produit = stripe.Product.create(name=f"KontrolIA {FONDATEUR['label']}",
                                        metadata={"app": "kontrolia", "plan": FONDATEUR["plan"]}).id
        stripe.Price.create(product=produit, currency="eur", unit_amount=FONDATEUR["monthly"], lookup_key=cle,
                            recurring={"interval": "month"}, nickname="Pro Fondateur mensuel")
        info(f"  Prix créé : {cle} = {FONDATEUR['monthly'] / 100:.2f} €")
    try:
        c = stripe.Coupon.retrieve(FONDATEUR["coupon"])
        info(f"  Coupon fondateur déjà présent ({c.times_redeemed or 0}/{c.max_redemptions} utilisé).")
    except stripe.error.InvalidRequestError:
        stripe.Coupon.create(id=FONDATEUR["coupon"], name="Programme Cabinet Fondateur",
                             amount_off=FONDATEUR["remise"], currency="eur", duration="repeating",
                             duration_in_months=FONDATEUR["mois_remise"], max_redemptions=FONDATEUR["places"],
                             metadata={"app": "kontrolia"})
        info(f"  Coupon créé : -{FONDATEUR['remise'] / 100:.2f} € pendant {FONDATEUR['mois_remise']} mois, "
             f"{FONDATEUR['places']} places.")
    info("1b/3 Offre fondateur prête.")


def portail(prix_par_produit, app_url):
    params = dict(
        business_profile={"headline": "KontrolIA — SMD Global Consulting LLC",
                          "privacy_policy_url": f"{app_url}/?doc=confidentialite",
                          "terms_of_service_url": f"{app_url}/?doc=cgu"},
        default_return_url=f"{app_url}/?stripe=portal_return",
        features={
            "customer_update": {"enabled": True, "allowed_updates": ["email", "address", "tax_id"]},
            "invoice_history": {"enabled": True},
            "payment_method_update": {"enabled": True},
            "subscription_cancel": {"enabled": True, "mode": "at_period_end"},
            "subscription_update": {"enabled": True, "default_allowed_updates": ["price"],
                                    "proration_behavior": "create_prorations",
                                    "products": [{"product": p, "prices": ids}
                                                 for p, ids in prix_par_produit.items()]},
        })
    existante = next((c for c in stripe.billing_portal.Configuration.list(active=True, limit=20).data
                      if _d(c).get("metadata", {}).get("app") == "kontrolia"), None)
    if existante:   # mise à jour sur place (la configuration par défaut ne peut pas être désactivée)
        stripe.billing_portal.Configuration.modify(existante.id, **params)
    else:
        stripe.billing_portal.Configuration.create(metadata={"app": "kontrolia"}, **params)
    info("2/3 Portail client configuré (changement de plan, résiliation en fin de période, factures).")


def webhook(app_url):
    url = f"{app_url}/webhook/stripe"
    for w in stripe.WebhookEndpoint.list(limit=100).data:
        if w.url == url:
            stripe.WebhookEndpoint.delete(w.id)
    w = stripe.WebhookEndpoint.create(url=url, enabled_events=EVENEMENTS, description="KontrolIA")
    info(f"3/3 Webhook créé : {url}")
    return w.secret


def taux_tva():
    """Taux de TVA française 20 %, ajouté aux prix HT sur chaque facture d'abonnement."""
    for t in stripe.TaxRate.list(active=True, limit=100).data:
        if _d(t).get("metadata", {}).get("app") == "kontrolia":
            info(f"0/3 Taux de TVA déjà présent : {t.percentage} % (hors taxe, ajouté au prix).")
            return t.id
    t = stripe.TaxRate.create(display_name="TVA", description="TVA France 20 %", jurisdiction="FR",
                              country="FR", percentage=20, inclusive=False, tax_type="vat",
                              metadata={"app": "kontrolia"})
    info("0/3 Taux de TVA créé : 20 % ajouté aux prix HT.")
    return t.id


def main():
    cle = _get_stripe_key()
    if not cle:
        sys.exit("STRIPE_SECRET_KEY absent de secrets.toml")
    stripe.api_key = cle
    app_url = _get_app_url().rstrip("/")
    if not app_url.startswith("https://"):
        sys.exit(f"APP_URL doit être l'adresse publique en https (actuellement « {app_url} »)")
    info(f"Compte Stripe en mode {'TEST' if cle.startswith(('sk_test_', 'rk_test_')) else 'RÉEL'} — {app_url}")
    if regime_tva() == "20":
        taux_tva()
    else:
        info("0/3 TVA : autoliquidation (aucun taux ajouté, mention en pied de facture).")
    prix = produits_et_prix()
    offre_fondateur()
    portail(prix, app_url)
    if "--sans-webhook" in sys.argv:          # mise à jour sans changer le secret du webhook
        info("3/3 Webhook inchangé.")
        return
    secret = webhook(app_url)
    print(f'STRIPE_WEBHOOK_SECRET = "{secret}"')


if __name__ == "__main__":
    main()
