# -*- coding: utf-8 -*-
"""
utils/page_tarifs.py — SMD Consulting
Page Tarifs & Abonnement partagée entre PCG France et SYSCOHADA.
"""

import streamlit as st
from utils.auth_rbac import PLANS, get_quota_used, get_user


# ─── Définition des plans avec features ──────────────────────────────────────

PLANS_DISPLAY = {
    "free": {
        "label":    "Gratuit",
        "price_m":  0,
        "price_a":  0,
        "quota":    10,
        "color":    "#6b7280",
        "badge":    "",
        "features": [
            "✅ 10 analyses / mois",
            "✅ Analyse de factures",
            "✅ Audit balance basique",
            "✅ Compte de résultat",
            "❌ Loi de Benford",
            "❌ FEC & Rapports clients",
            "❌ Support prioritaire",
        ],
    },
    "starter": {
        "label":    "Starter",
        "price_m":  29,
        "price_a":  279,
        "quota":    50,
        "color":    "#0891b2",
        "badge":    "",
        "features": [
            "✅ 50 analyses / mois",
            "✅ Tous les modules d'analyse",
            "✅ Loi de Benford",
            "✅ Export Word & Excel",
            "✅ FEC DGFiP",
            "❌ Rapports clients PDF",
            "❌ Support prioritaire",
        ],
    },
    "pro": {
        "label":    "Pro",
        "price_m":  79,
        "price_a":  759,
        "quota":    200,
        "color":    "#7c3aed",
        "badge":    "⭐ Populaire",
        "features": [
            "✅ 200 analyses / mois",
            "✅ Tous les modules",
            "✅ Rapports clients PDF",
            "✅ Plan de financement",
            "✅ TFT & Comparatif N/N-1",
            "✅ Gestion multi-collaborateurs",
            "✅ Support prioritaire",
        ],
    },
    "enterprise": {
        "label":    "Entreprise",
        "price_m":  199,
        "price_a":  1909,
        "quota":    -1,
        "color":    "#d97706",
        "badge":    "🏆 Cabinets",
        "features": [
            "✅ Analyses illimitées",
            "✅ Tous les modules",
            "✅ Multi-agents (PCG + SYSCOHADA)",
            "✅ Gestion cabinet & clients",
            "✅ Audit logs complets",
            "✅ Intégration Supabase dédiée",
            "✅ Support dédié & onboarding",
        ],
    },
}


def page_tarifs(app_name: str = "pcg") -> None:
    """
    Affiche la page Tarifs & Abonnement.
    app_name : 'pcg' | 'syscohada' | 'multi'
    """
    user_email  = st.session_state.get("user_email", "")
    plan_actuel = st.session_state.get("plan", "free")
    role        = st.session_state.get("role", "client")

    st.title("💳 Tarifs & Abonnement")
    st.markdown("Choisissez le plan adapté à votre activité. Sans engagement, résiliable à tout moment.")

    # ── Abonnement actuel ─────────────────────────────────────────────────────
    if plan_actuel != "free":
        info = PLANS_DISPLAY.get(plan_actuel, {})
        used = get_quota_used(user_email) if user_email else 0
        limit = info.get("quota", 0)
        limit_str = "illimité" if limit == -1 else str(limit)
        color = info.get("color", "#6b7280")
        st.markdown(f"""
            <div style='background:{color}12;border:1.5px solid {color}50;
                        padding:14px 20px;border-radius:10px;margin-bottom:20px'>
                <span style='color:{color};font-weight:700;font-size:1.05em'>
                    Plan actuel : {info.get("label","").upper()}
                </span>
                &nbsp;&nbsp;
                <span style='color:#555;font-size:0.9em'>
                    {used} / {limit_str} analyses utilisées ce mois
                </span>
            </div>
        """, unsafe_allow_html=True)

        col_portal, _ = st.columns([1, 3])
        with col_portal:
            if st.button("⚙️ Gérer mon abonnement", use_container_width=True):
                try:
                    from utils.stripe_billing import creer_portal_session
                    url = creer_portal_session(user_email, app_name)
                    st.markdown(f'<meta http-equiv="refresh" content="0;url={url}">',
                                unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Erreur portail : {e}")

        st.divider()

    # ── Sélecteur mensuel / annuel ─────────────────────────────────────────────
    col_left, col_right = st.columns([3, 1])
    with col_right:
        billing = st.radio("Facturation", ["Mensuelle", "Annuelle (-20%)"],
                           horizontal=False, label_visibility="collapsed")
    billing_key = "annual" if "Annuelle" in billing else "monthly"

    if billing_key == "annual":
        st.caption("💡 Économisez 2 mois avec la facturation annuelle.")

    # ── Tableau des plans ─────────────────────────────────────────────────────
    cols = st.columns(4, gap="small")

    for i, (plan_key, plan) in enumerate(PLANS_DISPLAY.items()):
        color    = plan["color"]
        is_current = (plan_key == plan_actuel)
        badge    = plan["badge"]
        price    = plan["price_a"] if billing_key == "annual" else plan["price_m"]
        period   = "/an" if billing_key == "annual" else "/mois"
        quota_str = "Illimité" if plan["quota"] == -1 else f"{plan['quota']}/mois"

        with cols[i]:
            # Badge populaire / cabinets
            if badge:
                st.markdown(f"""
                    <div style='background:{color};color:#fff;font-size:0.72em;
                                font-weight:700;padding:3px 10px;border-radius:12px;
                                text-align:center;margin-bottom:4px'>
                        {badge}
                    </div>
                """, unsafe_allow_html=True)

            # Carte plan
            border = f"2px solid {color}" if is_current else f"1px solid {color}40"
            bg     = f"{color}10" if is_current else "#fafafa"

            st.markdown(f"""
                <div style='border:{border};background:{bg};
                            border-radius:12px;padding:16px 14px 8px;
                            min-height:320px'>
                    <div style='color:{color};font-weight:800;font-size:1.1em'>
                        {plan["label"]}
                    </div>
                    <div style='font-size:2em;font-weight:900;
                                color:#1a1a1a;margin:6px 0 2px'>
                        {f"€{price}" if price > 0 else "Gratuit"}
                        <span style='font-size:0.4em;color:#888;font-weight:400'>
                            {period if price > 0 else ""}
                        </span>
                    </div>
                    <div style='font-size:0.8em;color:#888;margin-bottom:12px'>
                        {quota_str} analyses
                    </div>
                    <hr style='border:none;border-top:1px solid {color}30;margin:8px 0'>
                    {"".join(
                        f"<div style='font-size:0.78em;padding:3px 0;color:#444'>{f}</div>"
                        for f in plan["features"]
                    )}
                </div>
            """, unsafe_allow_html=True)

            # Bouton action
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            if is_current:
                st.button(
                    "✅ Plan actuel",
                    key=f"current_{plan_key}",
                    disabled=True,
                    use_container_width=True,
                )
            elif plan_key == "free":
                if plan_actuel != "free":
                    st.button(
                        "⬇️ Rétrograder",
                        key=f"downgrade_{plan_key}",
                        use_container_width=True,
                        disabled=True,
                        help="Résiliez votre abonnement via le portail client.",
                    )
            else:
                label = "🚀 Commencer" if plan_actuel == "free" else "⬆️ Upgrader"
                if st.button(label, key=f"checkout_{plan_key}",
                             use_container_width=True, type="primary"):
                    if not user_email:
                        st.error("Connectez-vous pour souscrire.")
                    else:
                        try:
                            from utils.stripe_billing import creer_checkout_session
                            nom = st.session_state.get("nom", "")
                            url = creer_checkout_session(
                                email=user_email, plan=plan_key,
                                app=app_name, billing=billing_key, nom=nom
                            )
                            st.markdown(
                                f'<meta http-equiv="refresh" content="0;url={url}">',
                                unsafe_allow_html=True
                            )
                        except Exception as e:
                            st.error(f"Erreur Stripe : {e}")

    # ── Pack multi-agents ──────────────────────────────────────────────────────
    st.divider()
    st.subheader("🤖 Pack Multi-Agents — PCG France + SYSCOHADA")
    st.markdown("""
    Accédez aux **deux plateformes** (France PCG + Zone OHADA) avec un seul abonnement.

    | Pack | Quota | Prix mensuel | Prix annuel |
    |------|-------|-------------|-------------|
    | Multi Starter | 100 analyses/mois | **€49/mois** | €469/an |
    | Multi Pro | 400 analyses/mois | **€129/mois** | €1 239/an |
    | Multi Entreprise | Illimité | **€299/mois** | €2 869/an |
    """)

    col_m1, col_m2, _ = st.columns([1, 1, 2])
    with col_m1:
        if st.button("🌍 Souscrire Multi Starter", use_container_width=True):
            _checkout_multi(user_email, "starter", billing_key)
    with col_m2:
        if st.button("🌍 Souscrire Multi Pro", use_container_width=True):
            _checkout_multi(user_email, "pro", billing_key)

    # ── FAQ ────────────────────────────────────────────────────────────────────
    st.divider()
    with st.expander("❓ Questions fréquentes"):
        st.markdown("""
**Puis-je changer de plan à tout moment ?**
Oui. Vous pouvez upgrader ou résilier depuis le portail client Stripe, sans frais de résiliation.

**Qu'est-ce qu'une « analyse » ?**
Chaque utilisation d'un module IA compte pour 1 analyse : audit balance, Benford, compte de résultat, FEC, rapport client, etc.

**Les données de mes clients sont-elles sécurisées ?**
Oui. Vos fichiers sont analysés en mémoire, jamais stockés de façon permanente. Conformité RGPD.

**Proposez-vous une période d'essai ?**
Le plan Gratuit vous permet de tester 10 analyses par mois sans carte bancaire.

**Factures disponibles ?**
Oui, toutes vos factures sont disponibles dans le portail client Stripe.

**Contact**
📧 contact@smdconsulting.pro
        """)


def _checkout_multi(user_email: str, plan: str, billing: str) -> None:
    if not user_email:
        st.error("Connectez-vous pour souscrire.")
        return
    try:
        from utils.stripe_billing import creer_checkout_session
        url = creer_checkout_session(user_email, plan, app="multi", billing=billing)
        st.markdown(f'<meta http-equiv="refresh" content="0;url={url}">', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Erreur Stripe : {e}")
