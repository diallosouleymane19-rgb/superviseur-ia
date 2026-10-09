# -*- coding: utf-8 -*-
"""
utils/page_inscription.py — SMD Global Consulting LLC
Page d'inscription publique avec choix de plan et onboarding Stripe.
Superviseur IA PCG France.
"""

import streamlit as st
import re
from utils.auth_rbac import creer_user_rbac, PLANS


# ─── Validation ───────────────────────────────────────────────────────────────

def _email_valide(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()))


def _mdp_fort(mdp: str) -> tuple[bool, str]:
    if len(mdp) < 8:
        return False, "8 caractères minimum"
    if not re.search(r"[A-Z]", mdp):
        return False, "Au moins une majuscule"
    if not re.search(r"[0-9]", mdp):
        return False, "Au moins un chiffre"
    return True, ""


# ─── Page principale ──────────────────────────────────────────────────────────

def page_inscription(app_name: str = "pcg") -> None:
    """
    Page d'inscription publique avec :
    - Formulaire de création de compte
    - Choix de plan
    - Redirect Stripe Checkout si plan payant
    """
    app_label = "Superviseur IA PCG France"

    # ── En-tête ───────────────────────────────────────────────────────────────
    st.markdown(f"""
        <div style='text-align:center;padding:32px 0 24px'>
            <div style='font-size:2.8em;font-weight:900;color:#1a3a5c'>
                SMD Global Consulting LLC
            </div>
            <div style='font-size:1.15em;color:#4a90d9;margin-top:4px'>
                {app_label}
            </div>
            <div style='font-size:0.9em;color:#888;margin-top:8px'>
                Créez votre compte et commencez à analyser en 2 minutes.
            </div>
        </div>
    """, unsafe_allow_html=True)

    col_form, col_right = st.columns([1, 1], gap="large")

    # ── Formulaire ────────────────────────────────────────────────────────────
    with col_form:
        st.subheader("📝 Créer mon compte")

        with st.form("form_inscription_publique", clear_on_submit=False):

            email = st.text_input(
                "📧 Email professionnel *",
                placeholder="contact@cabinet.com",
            )
            col_nom, col_prenom = st.columns(2)
            with col_nom:
                nom = st.text_input("👤 Nom *", placeholder="Diallo")
            with col_prenom:
                prenom = st.text_input("Prénom", placeholder="Souleymane")

            cabinet = st.text_input(
                "🏢 Cabinet / Entreprise",
                placeholder="Cabinet Comptable XYZ",
                help="Invité par un cabinet ? Utilisez l'e-mail de l'invitation : vous rejoindrez ce cabinet "
                     "automatiquement, ce champ et le plan seront ignorés.",
            )

            pays_options = {
                "🇫🇷 France":            "FR",
                "🇸🇳 Sénégal":           "SN",
                "🇨🇮 Côte d'Ivoire":     "CI",
                "🇨🇲 Cameroun":          "CM",
                "🇧🇫 Burkina Faso":      "BF",
                "🇲🇱 Mali":              "ML",
                "🇬🇳 Guinée":            "GN",
                "🇧🇯 Bénin":             "BJ",
                "🇹🇬 Togo":              "TG",
                "🇳🇪 Niger":             "NE",
                "🇬🇦 Gabon":             "GA",
                "🇨🇬 Congo":             "CG",
                "🌍 Autre":              "XX",
            }
            pays_label = st.selectbox("🌍 Pays", list(pays_options.keys()))
            pays_code  = pays_options[pays_label]

            st.markdown("---")

            # Choix du plan
            st.markdown("**💳 Choisissez votre plan**")
            plan_options = {
                "🆓 Gratuit — 10 analyses/mois (€0)":           "free",
                "🚀 Starter — 50 analyses/mois (€29/mois)":     "starter",
                "⭐ Pro — 200 analyses/mois (€79/mois)":        "pro",
                "🏆 Entreprise — Illimité (€199/mois)":         "enterprise",
            }
            plan_label  = st.selectbox("Plan", list(plan_options.keys()),
                                       label_visibility="collapsed")
            plan_choisi = plan_options[plan_label]

            if plan_choisi != "free":
                st.caption("💡 Vous serez redirigé vers Stripe pour payer en toute sécurité.")

            st.markdown("---")

            mdp  = st.text_input("🔑 Mot de passe *", type="password",
                                  help="8 caractères min, 1 majuscule, 1 chiffre")
            mdp2 = st.text_input("🔑 Confirmer le mot de passe *", type="password")

            cgv = st.checkbox("J'accepte les [Conditions Générales d'Utilisation](?doc=cgu) et la [Politique de Confidentialité](?doc=confidentialite)")

            submitted = st.form_submit_button(
                "✅ Créer mon compte" if plan_choisi == "free" else "✅ Créer et payer",
                width="stretch",
                type="primary",
            )

        # ── Traitement du formulaire ──────────────────────────────────────────
        if submitted:
            errors = []

            if not email or not _email_valide(email):
                errors.append("Email invalide.")
            if not nom.strip():
                errors.append("Le nom est requis.")
            if not mdp:
                errors.append("Le mot de passe est requis.")
            elif mdp != mdp2:
                errors.append("Les mots de passe ne correspondent pas.")
            else:
                ok_mdp, msg_mdp = _mdp_fort(mdp)
                if not ok_mdp:
                    errors.append(f"Mot de passe trop faible : {msg_mdp}.")
            if not cgv:
                errors.append("Vous devez accepter les CGU pour continuer.")

            if errors:
                for err in errors:
                    st.error(f"❌ {err}")
            else:
                nom_complet = f"{prenom.strip()} {nom.strip()}".strip()
                result = creer_user_rbac(
                    email   = email.strip().lower(),
                    password= mdp,
                    nom     = nom_complet,
                    cabinet = cabinet.strip(),
                    pays    = pays_code,
                    role    = "cabinet",   # responsable de son cabinet (ou collaborateur s'il a été invité)
                    plan    = "free",  # plan free d'abord, Stripe activera le plan payant
                )

                if "error" in result:
                    st.error(f"❌ {result['error']}")
                elif result.get("invite"):
                    # Invité par un cabinet : il le rejoint, l'abonnement est celui du cabinet
                    st.success(f"✅ Compte créé : vous avez rejoint « **{result.get('cabinet', '')}** » "
                               "en tant que collaborateur. Connectez-vous maintenant.")
                    st.session_state["inscription_ok"] = True
                    st.session_state["prefill_email"]  = email.strip().lower()
                else:
                    # Compte créé avec succès
                    if plan_choisi == "free":
                        st.success("✅ Compte créé ! Connectez-vous maintenant.")
                        st.balloons()
                        # Basculer vers l'onglet connexion
                        st.session_state["inscription_ok"] = True
                        st.session_state["prefill_email"]  = email.strip().lower()

                    else:
                        # Redirect vers Stripe Checkout
                        try:
                            from utils.stripe_billing import creer_checkout_session
                            url = creer_checkout_session(
                                email   = email.strip().lower(),
                                plan    = plan_choisi,
                                app     = app_name,
                                billing = "monthly",
                                nom     = nom_complet,
                            )
                            st.success("✅ Compte créé ! Redirection vers le paiement…")
                            st.markdown(
                                f'<meta http-equiv="refresh" content="2;url={url}">',
                                unsafe_allow_html=True
                            )
                            st.link_button("💳 Accéder au paiement Stripe", url,
                                           width="stretch")
                        except Exception as e:
                            st.warning(
                                f"Compte créé, mais erreur Stripe : {e}\n"
                                "Vous pouvez upgrader depuis la page Tarifs après connexion."
                            )

        # Lien retour connexion
        st.markdown("---")
        st.caption("Déjà un compte ? Revenez à l'écran de connexion.")

    # ── Colonne droite : avantages ─────────────────────────────────────────────
    with col_right:
        st.markdown("### Pourquoi rejoindre SMD ?")

        avantages = [
            ("🧠", "IA Comptable augmentée",
             "Analyse vos balances, FEC, factures et états financiers en quelques secondes."),
            ("⚖", "PCG France",
             "Analyses selon le Plan comptable général français."),
            ("🛡", "Données sécurisées",
             "Fichiers lus en mémoire, non enregistrés. Analyses sauvegardées à votre demande : 30 jours, dans l'UE."),
            ("📊", "Rapports professionnels",
             "KPIs, alertes colorées, tableaux structurés prêts pour vos clients."),
            ("🔔", "Veille fiscale automatique",
             "Actualités Bercy et BOFiP, échéances fiscales et barèmes URSSAF vérifiés."),
            ("🏆", "Plans adaptés",
             "Du cabinet solo à la structure multi-collaborateurs."),
        ]

        for icon, titre, desc in avantages:
            st.markdown(f"""
                <div style='display:flex;gap:12px;padding:10px 0;
                            border-bottom:1px solid #f0f0f0'>
                    <div style='font-size:1.6em;flex-shrink:0'>{icon}</div>
                    <div>
                        <div style='font-weight:700;color:#1a3a5c;font-size:0.92em'>
                            {titre}
                        </div>
                        <div style='color:#666;font-size:0.82em;margin-top:2px'>
                            {desc}
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # Indicateurs de confiance
        st.markdown("""
            <div style='background:#f0fdf4;border:1px solid #bbf7d0;
                        padding:12px 16px;border-radius:8px;font-size:0.82em'>
                ✅ <b>Sans engagement</b> — résiliable à tout moment<br>
                ✅ <b>Paiement sécurisé</b> — Stripe (3D Secure)<br>
                ✅ <b>Facture disponible</b> — portail client Stripe<br>
                ✅ <b>Support</b> — contact@smdconsulting.pro
            </div>
        """, unsafe_allow_html=True)
