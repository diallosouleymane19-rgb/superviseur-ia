# -*- coding: utf-8 -*-
"""
Applique le pied de facture actuel (identité du vendeur + mentions) à tous les clients Stripe de KontrolIA,
pour que leurs PROCHAINES factures le portent. Les factures déjà émises ne changent pas (normal).
Seuls les clients dont le pied a été posé par KontrolIA (il contient « SMD GLOBAL CONSULTING » ou
« Prestation de services ») sont modifiés : les autres clients du compte Stripe ne sont pas touchés.
Lancement (serveur) : cd /opt/superviseur/deploy && sudo docker compose exec -T app python scripts/stripe_pied_facture.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import stripe  # noqa: E402

from utils.stripe_billing import _d, _get_stripe_key, _mentions_facture  # noqa: E402

MARQUES = ("SMD GLOBAL CONSULTING", "Prestation de services", "prestation de services")


def a_mettre_a_jour(pied_actuel: str, pied_voulu: str) -> bool:
    return bool(pied_actuel) and pied_actuel != pied_voulu and any(m in pied_actuel for m in MARQUES)


def main():
    cle = _get_stripe_key()
    if not cle:
        sys.exit("STRIPE_SECRET_KEY absent de secrets.toml")
    stripe.api_key = cle
    voulu = _mentions_facture()
    vus = modifies = 0
    for c in stripe.Customer.list(limit=100).auto_paging_iter():
        vus += 1
        actuel = (_d(c).get("invoice_settings") or {}).get("footer") or ""
        if a_mettre_a_jour(actuel, voulu):
            stripe.Customer.modify(c.id, invoice_settings={"footer": voulu})
            modifies += 1
            print(f"  mis à jour : {c.email}")
    print(f"Pied de facture : {modifies} client(s) mis à jour sur {vus}.")


if __name__ == "__main__":
    main()
