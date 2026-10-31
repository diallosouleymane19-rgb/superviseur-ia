# -*- coding: utf-8 -*-
"""Passage de Stripe en mode réel : autoliquidation, offre fondateur, client du mode test absent en mode réel.
Aucun appel réseau : les fonctions Stripe sont simulées."""
import types
import pytest
import stripe
from utils import stripe_billing as sb


@pytest.fixture(autouse=True)
def sans_reseau(monkeypatch):
    monkeypatch.setattr(sb, "_init_stripe", lambda: None)
    monkeypatch.setattr(sb, "_get_app_url", lambda: "https://app.test")
    monkeypatch.delenv("STRIPE_TVA", raising=False)


def test_plan_fondateur_donne_les_droits_pro():
    assert sb.plan_depuis_cle("pcg_fondateur_monthly") == "pro"
    assert sb.plan_depuis_cle("pcg_pro_annual") == "pro"
    assert sb.plan_depuis_cle("pcg_inconnu_monthly") is None


def test_autoliquidation_par_defaut(monkeypatch):
    assert sb.regime_tva() == "autoliquidation"
    assert "283-2 du CGI" in sb._mentions_facture()
    monkeypatch.setattr(stripe.TaxRate, "list", lambda **k: pytest.fail("aucun taux en autoliquidation"))
    assert sb._taux_tva_id() is None
    monkeypatch.setenv("STRIPE_TVA", "20")
    assert sb.regime_tva() == "20" and "283-2" not in sb._mentions_facture()


def _checkout(monkeypatch, places=25):
    vu = {}
    monkeypatch.setattr(sb, "get_or_create_customer", lambda *a, **k: "cus_1")
    monkeypatch.setattr(sb, "abonnements_actifs", lambda c: [])
    monkeypatch.setattr(sb, "_price_id", lambda app, plan, billing: f"price_{plan}_{billing}")
    monkeypatch.setattr(sb, "places_fondateur", lambda: places)
    monkeypatch.setattr(stripe.Customer, "modify", lambda *a, **k: None)
    monkeypatch.setattr(stripe.checkout.Session, "create",
                        lambda **k: vu.update(k) or types.SimpleNamespace(url="https://pay"))
    return vu


def test_checkout_fondateur_remise_appliquee(monkeypatch):
    vu = _checkout(monkeypatch)
    assert sb.creer_checkout_session("a@b.fr", "fondateur", billing="annual") == "https://pay"
    assert vu["line_items"][0]["price"] == "price_fondateur_monthly"      # toujours mensuel
    assert vu["discounts"] == [{"coupon": "kontrolia_fondateur"}] and "allow_promotion_codes" not in vu
    assert "default_tax_rates" not in vu["subscription_data"]            # autoliquidation : pas de TVA ajoutée


def test_checkout_pro_classique_et_places_epuisees(monkeypatch):
    vu = _checkout(monkeypatch)
    sb.creer_checkout_session("a@b.fr", "pro")
    assert vu["allow_promotion_codes"] is True and "discounts" not in vu
    assert vu["payment_method_types"] == ["card"]                         # carte seule
    _checkout(monkeypatch, places=0)
    with pytest.raises(ValueError):
        sb.creer_checkout_session("a@b.fr", "fondateur")


def test_client_du_mode_test_recree_en_mode_reel(monkeypatch):
    import utils.auth_rbac as ar
    monkeypatch.setattr(ar, "get_user", lambda e: {"stripe_customer_id": "cus_test_ancien"})
    monkeypatch.setattr(ar, "mettre_a_jour_stripe", lambda *a: None)

    def introuvable(i):
        raise stripe.error.InvalidRequestError("No such customer", "id")
    monkeypatch.setattr(stripe.Customer, "retrieve", introuvable)
    monkeypatch.setattr(stripe.Customer, "list", lambda **k: types.SimpleNamespace(data=[]))
    monkeypatch.setattr(stripe.Customer, "create", lambda **k: types.SimpleNamespace(id="cus_live_nouveau"))
    assert sb.get_or_create_customer("a@b.fr") == "cus_live_nouveau"
    monkeypatch.setattr(stripe.Customer, "retrieve", lambda i: {"id": i})
    assert sb.get_or_create_customer("a@b.fr") == "cus_test_ancien"     # client existant : conservé
