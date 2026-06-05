# -*- coding: utf-8 -*-
"""
utils/page_tarifs.py — SMD Global Consulting LLC
Page Tarifs & Abonnement — utilise st.components.v1.html pour contourner
le sanitizer Streamlit et garantir le rendu HTML des cartes.
"""

import streamlit as st
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
            "Audit balance basique",
            "Compte de resultat",
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
            "Analyses illimitees",
            "Tous les modules",
            "Multi-agents PCG + SYSCOHADA",
            "Gestion cabinet & clients",
            "Audit logs complets",
            "Support dedie & onboarding",
        ],
        "locked": [],
    },
}


def _card_html(plan_key, plan, price, period, is_current):
    """Genere le HTML complet d'une carte plan."""
    color = plan["color"]
    border = "2px solid " + color if is_current else "1px solid " + color + "40"
    bg = color + "15" if is_current else "#fafafa"
    quota_str = "Illimite" if plan["quota"] == -1 else str(plan["quota"]) + "/mois"

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
            "EUR " + str(price)
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
        + quota_str + " analyses</div>"
        + "<hr style=\"border:none;border-top:1px solid #e5e7eb;margin:8px 0\">"
        + feats
        + current_banner
        + "</div>"
    )
    return html


def page_tarifs(app_name="pcg"):
    """Page Tarifs & Abonnement."""
    user_email  = st.session_state.get("user_email", "")
    plan_actuel = st.session_state.get("plan", "free")

    st.title("Tarifs & Abonnement")
    st.markdown("Choisissez le plan adapte a votre activite. Sans engagement, resiliable a tout moment.")

    # --- Abonnement actuel ---
    if plan_actuel != "free":
        info  = PLANS_DISPLAY.get(plan_actuel, {})
        used  = get_quota_used(user_email) if user_email else 0
        limit = info.get("quota", 0)
        limit_str = "illimite" if limit == -1 else str(limit)
        st.success(
            "Plan actuel : **" + info.get("label", "") + "**  —  "
            + str(used) + " / " + limit_str + " analyses utilisees ce mois"
        )
        if st.button("Gerer mon abonnement Stripe"):
            try:
                from utils.stripe_billing import creer_portal_session
                url = creer_portal_session(user_email, app_name)
                st.markdown(
                    "<meta http-equiv='refresh' content='0;url=" + url + "'>",
                    unsafe_allow_html=True
                )
            except Exception as e:
                st.error("Erreur portail : " + str(e))
        st.divider()

    # --- Facturation mensuelle / annuelle ---
    billing_choice = st.radio(
        "Facturation",
        ["Mensuelle", "Annuelle (-20%)"],
        horizontal=True,
        label_visibility="collapsed"
    )
    billing_key = "annual" if "Annuelle" in billing_choice else "monthly"
    if billing_key == "annual":
        st.caption("Economisez 2 mois avec la facturation annuelle.")

    st.markdown("---")

    # --- Cartes plans ---
    cols = st.columns(4, gap="small")
    for i, (plan_key, plan) in enumerate(PLANS_DISPLAY.items()):
        price     = plan["price_a"] if billing_key == "annual" else plan["price_m"]
        period    = "/an" if billing_key == "annual" else "/mois"
        is_current = (plan_key == plan_actuel)

        with cols[i]:
            card = _card_html(plan_key, plan, price, period, is_current)
            components.html(card, height=320, scrolling=False)
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

            if is_current:
                st.button("Plan actuel", key="cur_" + plan_key,
                          disabled=True, use_container_width=True)
            elif plan_key == "free":
                st.button("Retrograder", key="down_" + plan_key,
                          disabled=True, use_container_width=True,
                          help="Resiliez via le portail Stripe.")
            else:
                label = "Commencer" if plan_actuel == "free" else "Upgrader"
                if st.button(label, key="pay_" + plan_key,
                             use_container_width=True, type="primary"):
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
                            st.markdown(
                                "<meta http-equiv='refresh' content='0;url=" + url + "'>",
                                unsafe_allow_html=True
                            )
                        except Exception as e:
                            st.error("Erreur Stripe : " + str(e))

    # --- Pack multi-agents ---
    st.divider()
    st.subheader("Pack Multi-Agents — PCG France + SYSCOHADA")
    st.markdown(
        "Acces aux **deux plateformes** avec un seul abonnement.\n\n"
        "| Pack | Quota | Mensuel | Annuel |\n"
        "|------|-------|---------|--------|\n"
        "| Multi Starter | 100 analyses/mois | EUR 49 | EUR 469 |\n"
        "| Multi Pro | 400 analyses/mois | EUR 129 | EUR 1 239 |\n"
        "| Multi Entreprise | Illimite | EUR 299 | EUR 2 869 |\n"
    )

    col1, col2, _ = st.columns([1, 1, 2])
    with col1:
        if st.button("Multi Starter", use_container_width=True):
            _checkout_multi(user_email, "starter", billing_key, app_name)
    with col2:
        if st.button("Multi Pro", use_container_width=True):
            _checkout_multi(user_email, "pro", billing_key, app_name)

    # --- FAQ ---
    st.divider()
    with st.expander("Questions frequentes"):
        st.markdown("""
**Puis-je changer de plan ?** Oui, a tout moment depuis le portail Stripe.

**Qu'est-ce qu'une analyse ?** Chaque module IA utilise = 1 analyse (audit, Benford, bilan, rapport client...).

**Les donnees sont-elles securisees ?** Oui — fichiers analyses en memoire, jamais stockes. Conformite RGPD.

**Essai gratuit ?** Plan Gratuit : 10 analyses/mois sans carte bancaire.

**Contact :** contact@smdconsulting.pro
        """)


def _checkout_multi(user_email, plan, billing, app_name):
    if not user_email:
        st.error("Connectez-vous pour souscrire.")
        return
    try:
        from utils.stripe_billing import creer_checkout_session
        url = creer_checkout_session(user_email, plan, app="multi", billing=billing)
        st.markdown(
            "<meta http-equiv='refresh' content='0;url=" + url + "'>",
            unsafe_allow_html=True
        )
    except Exception as e:
        st.error("Erreur Stripe : " + str(e))
