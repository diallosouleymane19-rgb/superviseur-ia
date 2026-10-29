# -*- coding: utf-8 -*-
"""Essai Pro « Dossier Propre en 14 jours » : nécessite une base PostgreSQL de test (DATABASE_URL)."""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

pytestmark = pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="base PostgreSQL de test absente")


@pytest.fixture
def sb():
    from utils.db_supabase import get_supabase
    return get_supabase()


def _email():
    return f"essai-{uuid.uuid4().hex[:8]}@test.fr"


def _nettoyer(sb, email):
    from utils.auth_rbac import get_user
    u = get_user(email)
    sb.table("users").delete().eq("email", email).execute()
    if u and u.get("tenant_id"):
        sb.table("smd_cabinets").delete().eq("id", str(u["tenant_id"])).execute()


def _fin(sb, tenant, delta, **extra):
    sb.table("smd_cabinets").update({"essai_fin": (datetime.now(timezone.utc) + delta).isoformat(), **extra}) \
        .eq("id", str(tenant)).execute()


def test_inscription_demarre_l_essai_puis_retour_au_gratuit(sb):
    from utils.auth_rbac import creer_user_rbac, get_user
    from utils.essai import jours_restants, demarrer_essai
    from utils.cabinets import get_cabinet
    email = _email()
    try:
        r = creer_user_rbac(email, "MotDePasse!123", nom="Test", cabinet="Cabinet Essai", role="cabinet", plan="free")
        assert r.get("ok") and r["essai"] is True
        u = get_user(email)
        assert u["plan"] == "pro"
        assert jours_restants(get_cabinet(u["tenant_id"])) == 14
        assert demarrer_essai(u["tenant_id"], email) is False          # un seul essai par cabinet
        _fin(sb, u["tenant_id"], timedelta(minutes=-1))                 # essai échu
        u = get_user(email)
        assert u["plan"] == "free"
        assert get_cabinet(u["tenant_id"])["plan"] == "free"
        assert sb.table("users").select("plan").eq("email", email).execute().data[0]["plan"] == "free"
        assert demarrer_essai(u["tenant_id"], email) is False          # pas de second essai
    finally:
        _nettoyer(sb, email)


def test_abonne_stripe_jamais_repasse_au_gratuit(sb):
    from utils.auth_rbac import creer_user_rbac, get_user
    email = _email()
    try:
        creer_user_rbac(email, "MotDePasse!123", cabinet="Cabinet Abonné", role="cabinet", plan="free")
        t = get_user(email)["tenant_id"]
        _fin(sb, t, timedelta(days=-2), stripe_subscription_id="sub_test")
        assert get_user(email)["plan"] == "pro"
    finally:
        _nettoyer(sb, email)


def test_rappel_trois_jours_avant_une_seule_fois(sb, monkeypatch):
    from utils.auth_rbac import creer_user_rbac, get_user
    from utils import essai, email_envoi
    envoyes = []
    monkeypatch.setattr(email_envoi, "envoi_possible", lambda: True)
    monkeypatch.setattr(email_envoi, "envoyer_email", lambda d, s, t: envoyes.append((d, s, t)) or True)
    email = _email()
    try:
        creer_user_rbac(email, "MotDePasse!123", cabinet="Cabinet Rappel", role="cabinet", plan="free")
        t = get_user(email)["tenant_id"]
        _fin(sb, t, timedelta(days=2, hours=5))
        essai.taches_essais()
        essai.taches_essais()
        mes = [e for e in envoyes if e[0] == email]
        assert len(mes) == 1 and "se termine le" in mes[0][1] and "plan Gratuit" in mes[0][2]
    finally:
        _nettoyer(sb, email)


def test_tache_horaire_expire_et_essai_depuis_la_page(sb):
    from utils.auth_rbac import creer_user_rbac, get_user
    from utils.cabinets import get_cabinet
    from utils import essai
    email = _email()
    try:
        creer_user_rbac(email, "MotDePasse!123", cabinet="Cabinet Tâche", role="cabinet", plan="free")
        t = get_user(email)["tenant_id"]
        _fin(sb, t, timedelta(hours=-1))
        assert essai.taches_essais()["expires"] >= 1
        assert get_cabinet(t)["plan"] == "free"
        # cabinet Gratuit ancien, sans essai : il peut le démarrer depuis la page Abonnement
        sb.table("smd_cabinets").update({"essai_fin": None}).eq("id", str(t)).execute()
        assert essai.essai_possible(get_cabinet(t))
        assert essai.demarrer_essai(t, email) and get_user(email)["plan"] == "pro"
    finally:
        _nettoyer(sb, email)
