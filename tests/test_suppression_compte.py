# -*- coding: utf-8 -*-
"""Suppression d'un compte par l'administrateur (base PostgreSQL de test)."""
import os
import uuid
import pytest

pytestmark = pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="base PostgreSQL de test absente")


def _compte(cabinet="Cab Test"):
    from utils.auth_rbac import creer_user_rbac, get_user
    e = f"del-{uuid.uuid4().hex[:8]}@test.fr"
    assert creer_user_rbac(e, "MotDePasse!123", cabinet=cabinet, role="cabinet", plan="free").get("ok")
    return e, get_user(e)


def test_seul_membre_cabinet_et_donnees_supprimes():
    from utils.db_supabase import get_supabase
    from utils.cabinets import supprimer_compte, get_cabinet
    from utils.auth_rbac import log_action
    sb = get_supabase()
    e, u = _compte()
    t = str(u["tenant_id"])
    sb.table("clients").insert({"nom": "Dossier X", "user_email": e, "tenant_id": t}).execute()
    log_action(e, "login")
    r = supprimer_compte(e, "admin@smd.fr")
    assert r["ok"] and r["cabinet_supprime"]
    assert not sb.table("users").select("id").eq("email", e).execute().data
    assert get_cabinet(t) is None
    assert not sb.table("clients").select("id").eq("tenant_id", t).execute().data


def test_cabinet_a_plusieurs_membres_conserve():
    from utils.db_supabase import get_supabase
    from utils.cabinets import supprimer_compte, get_cabinet
    sb = get_supabase()
    e, u = _compte()
    t = str(u["tenant_id"])
    e2 = f"del-{uuid.uuid4().hex[:8]}@test.fr"
    sb.table("users").insert({"email": e2, "role": "collaborateur", "tenant_id": t, "password_hash": ""}).execute()
    try:
        r = supprimer_compte(e2, "admin@smd.fr")
        assert r["ok"] and not r["cabinet_supprime"]
        assert get_cabinet(t) is not None
    finally:
        supprimer_compte(e, "admin@smd.fr")


def test_refus_admin_et_soi_meme():
    from utils.db_supabase import get_supabase
    from utils.cabinets import supprimer_compte
    sb = get_supabase()
    e, u = _compte()
    assert "propre compte" in supprimer_compte(e, e)["error"]
    sb.table("users").update({"role": "admin"}).eq("email", e).execute()
    assert "administrateur" in supprimer_compte(e, "autre@smd.fr")["error"]
    sb.table("users").update({"role": "cabinet"}).eq("email", e).execute()
    assert supprimer_compte(e, "autre@smd.fr")["ok"]
