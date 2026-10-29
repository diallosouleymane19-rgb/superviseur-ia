# -*- coding: utf-8 -*-
"""
utils/page_tarifs.py — SMD Global Consulting LLC
Page Tarifs & Abonnement — utilise st.components.v1.html pour contourner
le sanitizer Streamlit et garantir le rendu HTML des cartes.
"""

import streamlit as st
import logging

import streamlit.components.v1 as components
from utils.auth_rbac import get_quota_used, get_user

# --- Plans ---
PLANS_DISPLAY = {
    "free": {
        "label": "Gratuit", "price_m": 0, "price_a": 0,
        "quota": 10, "color": "#6b7280", "badge": "",
        "features": [
            "10 analyses / mois",
            "Analyse de factures",
            "Contrôle de balance basique",
            "Compte de résultat",
        ],
        "locked": [
            "Loi de Benford",
            "FEC & Rapports clients",
            "Support prioritaire",
        ],
    },
    "starter": {
        "label": "Starter", "price_m": 29, "price_a": 279,
        "quota": 50, "color": "#0891b2", "badge": "",
        "features": [
            "50 analyses / mois",
            "Tous les modules d'analyse",
            "Loi de Benford",
            "Export Word & Excel",
            "FEC DGFiP",
        ],
        "locked": [
            "Rapports clients PDF",
            "Support prioritaire",
        ],
    },
    "pro": {
        "label": "Pro", "price_m": 79, "price_a": 759,
        "quota": 200, "color": "#7c3aed", "badge": "Populaire",
        "features": [
            "200 analyses / mois",
            "Tous les modules",
            "Rapports clients PDF",
            "Plan de financement & TFT",
            "Gestion multi-collaborateurs",
            "Support prioritaire",
        ],
        "locked": [],
    },
    "enterprise": {
        "label": "Entreprise", "price_m": 199, "price_a": 1909,
        "quota": -1, "color": "#d97706", "badge": "Cabinets",
        "features": [
            "Analyses illimitées",
            "Tous les modules",
            "Gestion cabinet & clients",
            "Journal des actions complet",
            "Support dédié & onboarding",
        ],
        "locked": [],
    },
}


def _card_html(plan_key, plan, price, period, is_current):
    """Génère le HTML complet d'une carte plan."""
    color = plan["color"]
    border = "2px solid " + color if is_current else "1px solid " + color + "40"
    bg = color + "15" if is_current else "#fafafa"
    quota_str = "Analyses illimitées" if plan["quota"] == -1 else str(plan["quota"]) + " analyses / mois"

    # Badge
    badge = ""
    if plan["badge"]:
        badge = (
            "<div style=\"background:" + color + ";color:#fff;font-size:11px;"
            "font-weight:700;padding:3px 10px;border-radius:12px;"
            "text-align:center;margin-bottom:6px;display:inline-block\">"
            + plan["badge"] + "</div><br>"
        )

    # Prix
    if price == 0:
        prix = "<div style=\"font-size:28px;font-weight:900;color:#1a1a1a;margin:6px 0 2px\">Gratuit</div>"
    else:
        prix = (
            "<div style=\"font-size:28px;font-weight:900;color:#1a1a1a;margin:6px 0 2px\">"
            + f"{price:,}".replace(",", "&#8239;") + "&nbsp;€&nbsp;<span style=\"font-size:13px;font-weight:600\">HT</span>"
            + "<span style=\"font-size:13px;color:#888;font-weight:400\">&nbsp;"
            + period + "</span></div>"
        )

    # Features
    feats = ""
    for f in plan["features"]:
        feats += "<div style=\"font-size:12px;padding:3px 0;color:#333\">&#10003; " + f + "</div>"
    for f in plan["locked"]:
        feats += "<div style=\"font-size:12px;padding:3px 0;color:#bbb\">&#10007; " + f + "</div>"

    current_banner = ""
    if is_current:
        current_banner = (
            "<div style=\"background:" + color + "20;color:" + color
            + ";font-size:11px;font-weight:700;text-align:center;"
            "padding:4px;border-radius:4px;margin-top:8px\">Plan actuel</div>"
        )

    html = (
        badge
        + "<div style=\"border:" + border + ";background:" + bg
        + ";border-radius:12px;padding:16px 14px 12px;font-family:sans-serif\">"
        + "<div style=\"color:" + color + ";font-weight:800;font-size:16px\">"
        + plan["label"] + "</div>"
        + prix
        + "<div style=\"font-size:12px;color:#888;margin-bottom:10px\">"
        + quota_str + "</div>"
        + "<hr style=\"border:none;border-top:1px solid #e5e7eb;margin:8px 0\">"
        + feats
        + current_banner
        + "</div>"
    )
    return html


def page_tarifs(app_name="pcg"):
    """Page Tarifs & Abonnement."""
    user_email  = st.session_state.get("user_email", "")
    # Plan relu en base : il change quand Stripe confirme un paiement (webhook), pendant la session
    u = None
    try:
        u = get_user(user_email) if user_email else None
        if u and u.get("plan"):
            st.session_state["plan"] = u["plan"]
    except Exception:
        pass
    plan_actuel = st.session_state.get("plan", "free")

    st.title("Abonnement")
    st.markdown("Choisissez le plan adapté à votre activité. Sans engagement, résiliable à tout moment.")
    # L'abonnement et le quota sont ceux du cabinet : seul son responsable les modifie
    collaborateur = st.session_state.get("role") == "collaborateur"
    if collaborateur:
        st.info(f"L'abonnement est commun à tous les membres de « **{st.session_state.get('cabinet', '')}** » "
                "et géré par son responsable. Adressez-vous à lui pour changer de plan.")

    from utils.stripe_billing import paiement_actif
    paiement_ok = paiement_actif()
    if not paiement_ok:
        st.info("Le paiement en ligne n'est pas encore activé. Pour changer de plan, écrivez à contact@smdconsulting.pro.", icon=":material/info:")

    # --- Essai Pro « Dossier Propre en 14 jours » ---
    from utils.essai import jours_restants, essai_possible, demarrer_essai, NOM_ESSAI, ESSAI_JOURS, _date
    from utils.cabinets import get_cabinet
    cab = get_cabinet(u.get("tenant_id")) if u else None
    j_essai = jours_restants(cab) if cab else None
    if j_essai:
        fin = _date(cab.get("essai_fin")).astimezone().strftime("%d/%m/%Y")
        st.info(f"Essai Pro « **{NOM_ESSAI}** » en cours : **{j_essai} jour{'s' if j_essai > 1 else ''}** "
                f"restant{'s' if j_essai > 1 else ''} (fin le {fin}). Tous les modules et 200 analyses par mois. "
                "Choisissez un plan ci-dessous pour continuer après l'essai ; sinon, le cabinet repassera "
                "au plan Gratuit, sans perdre ses dossiers.", icon=":material/timer:")
    elif cab and essai_possible(cab) and not collaborateur:
        st.markdown(f"#### Essayez le plan Pro {ESSAI_JOURS} jours, sans carte bancaire")
        st.caption(f"« {NOM_ESSAI} » : tous les modules, 200 analyses, sur vos vrais dossiers. "
                   "À la fin de l'essai, le cabinet repasse au plan Gratuit sauf si vous choisissez un plan.")
        if st.button(f"Démarrer mon essai Pro de {ESSAI_JOURS} jours", type="primary", icon=":material/rocket_launch:"):
            if demarrer_essai(cab["id"], user_email):
                st.session_state["plan"] = "pro"
                st.rerun()
            st.error("L'essai n'a pas pu démarrer. Réessayez ou écrivez à contact@smdconsulting.pro.")
        st.divider()
    elif cab and cab.get("essai_fin") and plan_actuel == "free":
        st.caption(f"Essai Pro terminé le {_date(cab.get('essai_fin')).astimezone().strftime('%d/%m/%Y')}.")

    # --- Abonnement actuel ---
    if plan_actuel != "free" and not j_essai:
        info  = PLANS_DISPLAY.get(plan_actuel, {})
        used  = get_quota_used(user_email) if user_email else 0
        limit = info.get("quota", 0)
        detail = (f"analyses illimitées ({used} utilisée{'s' if used > 1 else ''} ce mois par le cabinet)"
                  if limit == -1 else f"{used} / {limit} analyses utilisées ce mois par le cabinet")
        st.success("Plan actuel : **" + info.get("label", "") + "** — " + detail)
        if st.button("Gérer mon abonnement Stripe", disabled=collaborateur or not paiement_ok):
            try:
                from utils.stripe_billing import creer_portal_session
                url = creer_portal_session(user_email, app_name)
                st.link_button("Ouvrir le portail Stripe (nouvel onglet)", url, type="primary",
                               icon=":material/open_in_new:")
            except Exception:
                logging.exception("Portail Stripe")
                st.error("Le portail de paiement ne répond pas. Réessayez plus tard ou écrivez à contact@smdconsulting.pro.")
        st.divider()

    # --- Facturation mensuelle / annuelle ---
    billing_choice = st.radio(
        "Facturation",
        ["Mensuelle", "Annuelle (-20%)"],
        horizontal=True,
        label_visibility="collapsed"
    )
    billing_key = "annual" if "Annuelle" in billing_choice else "monthly"
    st.caption("Prix hors taxes : TVA française de 20 % en sus.")
    if billing_key == "annual":
        st.caption("Économisez 2 mois avec la facturation annuelle.")

    st.markdown("---")

    # --- Cartes plans ---
    cols = st.columns(4, gap="small")
    for i, (plan_key, plan) in enumerate(PLANS_DISPLAY.items()):
        price     = plan["price_a"] if billing_key == "annual" else plan["price_m"]
        period    = "/an" if billing_key == "annual" else "/mois"
        is_current = (plan_key == plan_actuel) and not j_essai   # pendant l'essai, le Pro reste à souscrire

        with cols[i]:
            card = _card_html(plan_key, plan, price, period, is_current)
            components.html(card, height=320, scrolling=False)
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

            if is_current:
                st.button("Plan actuel", key="cur_" + plan_key,
                          disabled=True, width="stretch")
            elif plan_key == "free":
                st.button("Rétrograder", key="down_" + plan_key,
                          disabled=True, width="stretch",
                          help="Résiliez via le portail Stripe.")
            else:
                label = "Commencer" if plan_actuel == "free" or j_essai else "Upgrader"
                if st.button(label, key="pay_" + plan_key, disabled=collaborateur or not paiement_ok,
                             width="stretch", type="primary"):
                    if not user_email:
                        st.error("Connectez-vous pour souscrire.")
                    else:
                        try:
                            from utils.stripe_billing import creer_checkout_session
                            url = creer_checkout_session(
                                email=user_email,
                                plan=plan_key,
                                app=app_name,
                                billing=billing_key,
                                nom=st.session_state.get("nom", ""),
                            )
                            st.link_button("Payer sur Stripe (paiement sécurisé, nouvel onglet)", url,
                                           type="primary", icon=":material/lock:", width="stretch")
                            st.caption("Après le paiement, revenez sur cet onglet et actualisez la page : "
                                       "le nouveau plan s'affiche en quelques secondes.")
                        except Exception as e:
                            from utils.stripe_billing import DejaAbonne
                            if isinstance(e, DejaAbonne):
                                st.info("Vous avez déjà un abonnement : pour changer de plan, utilisez "
                                        "« Gérer mon abonnement Stripe » en haut de cette page.",
                                        icon=":material/info:")
                                continue
                            logging.exception("Paiement Stripe")
                            st.error("Le paiement en ligne ne répond pas. Réessayez plus tard ou écrivez à contact@smdconsulting.pro.")

    # --- FAQ ---
    st.divider()
    with st.expander("Questions fréquentes"):
        st.markdown("""
**Puis-je changer de plan ?** Oui, à tout moment depuis le portail Stripe.

**Qu'est-ce qu'une analyse ?** Chaque calcul lancé compte pour 1 analyse : générer un bilan, contrôler une balance ou un FEC, analyser un lot de factures, lancer une analyse IA… Réafficher un résultat déjà calculé ne compte pas.

**Les données sont-elles sécurisées ?** Les fichiers déposés sont lus en mémoire et ne sont pas enregistrés. Seules les analyses que vous sauvegardez sont conservées, en France (OVH), 30 jours maximum.

**Essai gratuit ?** Oui : essai Pro « Dossier Propre en 14 jours », sans carte bancaire, une fois par cabinet. Ensuite, le plan Gratuit reste disponible (10 analyses/mois).

**Contact :** contact@smdconsulting.pro
        """)

