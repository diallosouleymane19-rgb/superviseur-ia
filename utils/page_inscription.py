# -*- coding: utf-8 -*-
"""
utils/page_inscription.py — SMD Global Consulting LLC
Page d'inscription publique avec choix de plan et onboarding Stripe.
Superviseur IA PCG France.
"""

import streamlit as st
import re
from utils.auth_rbac import creer_user_rbac, PLANS


@st.cache_data(ttl=300, show_spinner=False)
def _places_fondateur() -> int:
    """Places restantes du Programme Cabinet Fondateur (relu dans Stripe au plus toutes les 5 minutes)."""
    from utils.stripe_billing import places_fondateur
    return places_fondateur()


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
    app_label = "KontrolIA"

    # ── En-tête ───────────────────────────────────────────────────────────────
    st.markdown(f"""
        <div style='text-align:center;padding:32px 0 24px'>
            <div style='font-size:2.8em;font-weight:900;color:#1a3a5c'>
                {app_label}
            </div>
            <div style='font-size:1.15em;color:#4a90d9;margin-top:4px'>
                « Vous décidez, votre assistant {app_label} vérifie »
            </div>
            <div style='font-size:0.9em;color:#888;margin-top:8px'>
                Créez votre compte et commencez à analyser en 2 minutes.
            </div>
            <div style='font-size:0.75em;color:#9aa5b1;margin-top:6px'>
                une solution SMD Global Consulting LLC
            </div>
        </div>
    """, unsafe_allow_html=True)

    col_form, col_right = st.columns([1, 1], gap="large")

    # ── Formulaire ────────────────────────────────────────────────────────────
    with col_form:
        st.subheader("Créer mon compte")

        with st.form("form_inscription_publique", clear_on_submit=False):

            email = st.text_input(
                "Email professionnel *",
                placeholder="contact@cabinet.com",
            )
            col_nom, col_prenom = st.columns(2)
            with col_nom:
                nom = st.text_input("Nom *", placeholder="Diallo")
            with col_prenom:
                prenom = st.text_input("Prénom", placeholder="Souleymane")

            cabinet = st.text_input(
                "Cabinet / Entreprise",
                placeholder="Cabinet Comptable XYZ",
                help="Invité par un cabinet ? Utilisez l'e-mail de l'invitation : vous rejoindrez ce cabinet "
                     "automatiquement, ce champ et le plan seront ignorés.",
            )

            pays_options = {
                "France":            "FR",
                "Sénégal":           "SN",
                "Côte d'Ivoire":     "CI",
                "Cameroun":          "CM",
                "Burkina Faso":      "BF",
                "Mali":              "ML",
                "Guinée":            "GN",
                "Bénin":             "BJ",
                "Togo":              "TG",
                "Niger":             "NE",
                "Gabon":             "GA",
                "Congo":             "CG",
                "Autre":              "XX",
            }
            pays_label = st.selectbox("Pays", list(pays_options.keys()))
            pays_code  = pays_options[pays_label]

            st.markdown("---")

            # Choix du plan
            st.markdown("**Choisissez votre plan**")
            plan_options = {
                "Essai Pro 14 jours offert, puis Gratuit (0\u00a0€)":   "free",
                "Starter — 50 analyses/mois (29\u00a0€ HT/mois)":       "starter",
                "Pro — 200 analyses/mois (79\u00a0€ HT/mois)":          "pro",
                "Entreprise — analyses illimitées (199\u00a0€ HT/mois)": "enterprise",
            }
            from utils.stripe_billing import paiement_actif
            if not paiement_actif():   # sans paiement en ligne, seul le plan Gratuit est proposé
                plan_options = {k: v for k, v in plan_options.items() if v == "free"}
                st.caption("Plans payants : le paiement en ligne arrive bientôt. Écrivez à contact@smdconsulting.pro.")
            else:   # Programme Cabinet Fondateur, tant qu'il reste des places (proposé juste après l'essai)
                places = _places_fondateur()
                if places > 0:
                    libelle = (f"Pro Fondateur — 29,99\u00a0€ HT/mois 3 mois, puis 49,99\u00a0€ garanti "
                               f"({places} place{'s' if places > 1 else ''} sur 25)")
                    items = list(plan_options.items())
                    plan_options = dict(items[:1] + [(libelle, "fondateur")] + items[1:])
            # Plan choisi sur la page de présentation (bouton « Choisir … ») : présélectionné s'il est proposé
            codes = list(plan_options.values())
            prefere = st.session_state.get("plan_vitrine")
            plan_label  = st.selectbox("Plan", list(plan_options.keys()),
                                       index=codes.index(prefere) if prefere in codes else 0,
                                       label_visibility="collapsed")
            plan_choisi = plan_options[plan_label]

            if plan_choisi == "fondateur":
                st.caption("Plan Pro complet (tous les modules, 200 analyses par mois) au tarif fondateur, sans "
                           "engagement. Vous serez redirigé vers Stripe pour payer en toute sécurité ; renseignez votre "
                           "n° de TVA intracommunautaire (TVA autoliquidée).")
            elif plan_choisi != "free":
                st.caption("Vous serez redirigé vers Stripe pour payer en toute sécurité.")
            else:
                st.caption("« Dossier Propre en 14 jours » : plan Pro complet (tous les modules, 200 analyses), "
                           "sans carte bancaire. Ensuite, plan Gratuit (10 analyses/mois) sauf si vous choisissez un plan.")

            st.markdown("---")

            mdp  = st.text_input("Mot de passe *", type="password",
                                  help="8 caractères min, 1 majuscule, 1 chiffre")
            mdp2 = st.text_input("Confirmer le mot de passe *", type="password")

            cgv = st.checkbox("J'accepte les [Conditions Générales d'Utilisation](?doc=cgu) et la [Politique de Confidentialité](?doc=confidentialite)")

            submitted = st.form_submit_button(
                "Créer mon compte" if plan_choisi == "free" else "Créer et payer",
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
                    st.error(f"{err}", icon=":material/error:")
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
                    st.error(f"{result['error']}", icon=":material/error:")
                elif result.get("invite"):
                    # Invité par un cabinet : il le rejoint, l'abonnement est celui du cabinet
                    st.success(f"Compte créé : vous avez rejoint « **{result.get('cabinet', '')}** » "
                               "en tant que collaborateur. Connectez-vous maintenant.", icon=":material/check_circle:")
                    st.session_state["inscription_ok"] = True
                    st.session_state["prefill_email"]  = email.strip().lower()
                else:
                    # Compte créé avec succès
                    if plan_choisi == "free":
                        st.success("Compte créé ! " + ("Votre essai Pro « Dossier Propre en 14 jours » est activé, sans "
                                   "carte bancaire : tous les modules et 200 analyses pendant 14 jours. "
                                   if result.get("essai") else "") + "Connectez-vous maintenant.",
                                   icon=":material/check_circle:")
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
                            st.success("Compte créé ! Redirection vers le paiement…", icon=":material/check_circle:")
                            st.markdown(
                                f'<meta http-equiv="refresh" content="2;url={url}">',
                                unsafe_allow_html=True
                            )
                            st.link_button("Accéder au paiement Stripe", url,
                                           width="stretch")
                        except Exception:
                            import logging
                            logging.exception("Paiement Stripe à l'inscription")
                            st.warning("Compte créé en plan Gratuit, mais le paiement en ligne ne répond pas. "
                                       "Vous pourrez changer de plan depuis la page Abonnement après connexion.")

        # Lien retour connexion
        st.markdown("---")
        st.caption("Déjà un compte ? Revenez à l'écran de connexion.")

    # ── Colonne droite : avantages ─────────────────────────────────────────────
    with col_right:
        st.markdown("### Pourquoi choisir KontrolIA ?")

        avantages = [
            ("🧠", "IA Comptable augmentée",
             "Analyse vos balances, FEC, factures et états financiers en quelques secondes."),
            ("⚖", "PCG France",
             "Analyses selon le Plan comptable général français."),
            ("🛡", "Données sécurisées",
             "Fichiers lus en mémoire, non enregistrés. Analyses sauvegardées à votre demande : 30 jours, en France (OVH)."),
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
                <b>Sans engagement</b> — résiliable à tout moment<br>
                <b>Paiement sécurisé</b> — Stripe (3D Secure)<br>
                <b>Facture disponible</b> — portail client Stripe<br>
                <b>Support</b> — contact@smdconsulting.pro
            </div>
        """, unsafe_allow_html=True)
