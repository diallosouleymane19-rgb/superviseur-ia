# -*- coding: utf-8 -*-
"""Page « Mon cabinet » : nom, abonnement partagé, membres et invitations des collaborateurs."""
from html import escape

import streamlit as st

from utils import cabinets as C
from utils.auth_rbac import PLANS, get_role_label


def _date(x):
    return str(x)[8:10] + "/" + str(x)[5:7] + "/" + str(x)[:4] if x else "—"


def _lien_app():
    try:
        return st.secrets.get("APP_URL", "") or ""
    except Exception:
        return ""


def _inviter(tenant_id, par):
    email = st.session_state.get("cab_invite_email", "")
    r = C.inviter(tenant_id, email, par)
    if r.get("ok"):
        st.session_state["cab_message"] = ("success", f"Invitation enregistrée pour {email.strip().lower()}.")
        st.session_state["cab_invite_email"] = ""
    else:
        st.session_state["cab_message"] = ("error", r["error"])


def _annuler(tenant_id, inv_id, email):
    ok = C.annuler_invitation(tenant_id, inv_id)
    st.session_state["cab_message"] = ("success", f"Invitation de {email} annulée.") if ok \
        else ("error", "Annulation impossible.")


def _retirer(tenant_id, email, par):
    r = C.retirer_membre(tenant_id, email, par)
    st.session_state["cab_message"] = ("success", f"{email} a été retiré du cabinet : son compte est fermé.") \
        if r.get("ok") else ("error", r["error"])


def _renommer(tenant_id):
    nom = st.session_state.get("cab_nom", "")
    if C.renommer_cabinet(tenant_id, nom):
        st.session_state["cabinet"] = nom.strip()
        st.session_state["cab_message"] = ("success", "Nom du cabinet mis à jour.")
    else:
        st.session_state["cab_message"] = ("error", "Le nom ne peut pas être vide.")


def page_cabinet():
    st.title("👥 Mon cabinet")
    role = st.session_state.get("role", "")
    tenant_id = st.session_state.get("tenant_id")
    email = st.session_state.get("user_email", "")

    if role == "demo":
        st.info("En mode démonstration, il n'y a pas de cabinet. Créez un compte gratuit pour inviter vos collaborateurs.")
        return
    cab = C.get_cabinet(tenant_id)
    if not cab:
        st.info("Votre compte n'est rattaché à aucun cabinet.")
        return

    responsable = role == C.ROLE_RESPONSABLE
    msg = st.session_state.pop("cab_message", None)
    if msg:
        (st.success if msg[0] == "success" else st.error)(msg[1])

    plan = PLANS.get(cab.get("plan") or "free", PLANS["free"])
    quota = "illimité" if plan["quota"] == -1 else f"{plan['quota']} analyses par mois"
    st.markdown(f"**{escape(cab.get('nom', ''))}** · plan **{plan['label']}** ({quota}), commun à tous les membres.")
    st.caption("Les dossiers clients et les analyses sauvegardées sont partagés entre tous les membres du cabinet.")

    if responsable:
        with st.expander("Modifier le nom du cabinet"):
            st.text_input("Nom du cabinet", value=cab.get("nom", ""), key="cab_nom")
            st.button("Enregistrer", on_click=_renommer, args=(tenant_id,), key="cab_btn_nom")

    st.subheader("Membres")
    for m in C.membres(tenant_id):
        c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
        c1.markdown(f"**{escape(m.get('nom') or m['email'])}**  \n{escape(m['email'])}")
        c2.markdown(get_role_label(m.get("role", "")))
        c3.caption(f"Dernière connexion : {_date(m.get('last_login'))}")
        if responsable and m.get("role") == C.ROLE_COLLABORATEUR:
            c4.button("Retirer", key=f"cab_ret_{m['email']}", on_click=_retirer, args=(tenant_id, m["email"], email),
                      help="Ferme le compte du collaborateur. Ses analyses restent dans le cabinet.")

    if not responsable:
        st.caption("Seul le responsable du cabinet peut inviter ou retirer des collaborateurs.")
        return

    st.subheader("Inviter un collaborateur")
    c1, c2 = st.columns([3, 1])
    c1.text_input("E-mail professionnel du collaborateur", key="cab_invite_email",
                  placeholder="prenom.nom@cabinet.fr", label_visibility="collapsed")
    c2.button("Inviter", type="primary", width="stretch", on_click=_inviter, args=(tenant_id, email), key="cab_btn_inv")
    lien = _lien_app()
    st.caption("L'appli n'envoie pas d'e-mail : prévenez vous-même votre collaborateur. Il ouvre l'application"
               + (f" ({lien})" if lien else "") + ", onglet **Créer un compte**, avec cette adresse e-mail : "
               "il rejoint automatiquement votre cabinet. L'invitation est valable 30 jours.")

    attente = C.invitations_en_attente(tenant_id)
    if attente:
        st.subheader("Invitations en attente")
        for inv in attente:
            c1, c2, c3 = st.columns([4, 3, 2])
            c1.markdown(escape(inv["email"]))
            c2.caption(f"Envoyée le {_date(inv.get('created_at'))} · expire le {_date(inv.get('expires_at'))}")
            c3.button("Annuler", key=f"cab_ann_{inv['id']}", on_click=_annuler, args=(tenant_id, inv["id"], inv["email"]))
