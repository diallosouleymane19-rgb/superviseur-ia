# -*- coding: utf-8 -*- 
"""
Superviseur IA Comptable - SMD Global Consulting LLC
Application complète de supervision comptable augmentée par IA
Auteur: Souleymane Diallo
"""

from utils.formats import est_tableur, TYPES_BALANCE, TYPES_TABLEUR_CSV
import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Imports des modules utils
from utils.ai import appel_mistral, extraire_contenu_mistral, appel_mistral_vision
from utils.export_word import export_analyse_word
from utils.database import init_db, sauvegarder_analyse
from utils.rendu_financier import afficher_rapport, afficher_synthese_score
from utils.permissions import afficher_badge_role, afficher_quota_sidebar, check_quota, log_user_action
from utils.bilan import generer_bilan
from utils.rapprochement import rapprocher_bancaire
from utils.rapport_client import generer_rapport_client
from utils.alertes import detecter_alertes
from utils.coherence import verifier_coherence
from utils.security import sanitize_filename, sanitize_html_value
# Modules lourds en lazy dans leurs blocs (cold start optimise) :
# utils.ocr, utils.veille_fiscale, utils.fec, utils.plan_financement,
# utils.tft, utils.comparatif, utils.tva, utils.benford_module

# Authentification
from auth import login, logout, is_connecte

# =============================================================================
# CONFIGURATION DE L'APPLICATION
# =============================================================================

st.set_page_config(
    page_title="SMD Global Consulting LLC - Superviseur IA", 
    layout="wide", 
    page_icon="🔒",
    initial_sidebar_state="auto"
)

# Charte graphique
from utils.theme import appliquer_theme

# Graphiques Plotly : virgule décimale et espace pour les milliers (1 234,5)
try:
    import plotly.io as _pio
    import plotly.graph_objects as _go
    _pio.templates["fr"] = _go.layout.Template(layout={"separators": ", "})
    _pio.templates.default = "plotly+fr"
except Exception:
    pass
appliquer_theme()

# Initialisation de la base de données
init_db()

# RGPD : suppression automatique des analyses sauvegardées depuis plus de 30 jours (au plus 1 fois / heure)
from utils.database import purger_si_necessaire
purger_si_necessaire()

# Pages légales (CGU, confidentialité) : consultables sans connexion via ?doc=cgu / ?doc=confidentialite
_doc_legal = st.query_params.get("doc")
if _doc_legal:
    from utils.pages_legales import afficher_document
    if afficher_document(_doc_legal):
        st.stop()

# =============================================================================
# AUTHENTIFICATION
# =============================================================================

if not is_connecte():
    # Retour Stripe éventuel (upgrade depuis login)
    from utils.stripe_billing import gerer_retour_stripe
    gerer_retour_stripe()

    # Venant du bouton « Tester gratuitement » : l'onglet d'inscription s'ouvre en premier
    if st.session_state.get("ouvrir_inscription"):
        tab_signup, tab_login = st.tabs(["Créer un compte", "Se connecter"])
    else:
        tab_login, tab_signup = st.tabs(["Se connecter", "Créer un compte"])

    with tab_login:
        col_marque, _, col_form = st.columns([5, 1, 4])
        with col_marque:
            st.markdown(
                "<div class='smd-marque'>SMD Global Consulting LLC</div>"
                "<h1 style='margin:0 0 .75rem'>Superviseur IA Comptable</h1>"
                "<p class='smd-accroche'>Analyse et supervision comptable pour les cabinets, "
                "conformes au PCG et aux exigences de la DGFiP.</p>"
                "<ul class='smd-engagements'>"
                "<li>Fichiers non enregistrés <span>: lus en mémoire le temps de l'analyse</span></li>"
                "<li>Sauvegardes limitées <span>: à votre demande, dans l'UE, supprimées après 30 jours</span></li>"
                "<li>IA signalée <span>: tout texte rédigé par l'IA (Mistral AI) est identifié</span></li>"
                "<li>Non utilisées pour entraîner l'IA <span>: option désactivée chez Mistral depuis le 07/10/2026</span></li>"
                "</ul>",
                unsafe_allow_html=True,
            )
        with col_form:
            prefill = st.session_state.pop("prefill_email", "")
            with st.form("form_connexion", border=True):
                st.markdown("#### Connexion")
                email    = st.text_input("Email professionnel", value=prefill,
                                         placeholder="contact@cabinet.com")
                password = st.text_input("Mot de passe", type="password")
                envoye = st.form_submit_button("Se connecter", type="primary", width="stretch")
            if envoye:
                if login(email, password):
                    st.rerun()
                else:
                    st.error("Email ou mot de passe incorrect. Vérifiez la saisie ou demandez un accès.")

            if st.button("Essayer la démonstration", width="stretch", key="btn_demo"):
                st.session_state.update({
                    "authenticated": True,
                    "user_email":    "demo@smdconsulting.pro",
                    "role":          "demo",
                    "plan":          "free",
                    "nom":           "Démonstration",
                    "login_time":    datetime.now().isoformat(),
                })
                st.rerun()
            st.caption("Demander un accès : contact@smdconsulting.pro")

        st.caption("SMD Global Consulting LLC © 2026 · [CGU](?doc=cgu) · "
                   "[Politique de confidentialité](?doc=confidentialite)")

    with tab_signup:
        from utils.page_inscription import page_inscription
        page_inscription(app_name="pcg")

    st.stop()

st.session_state.pop("ouvrir_inscription", None)   # connecté : ordre normal des onglets la prochaine fois

# =============================================================================
# SIDEBAR - NAVIGATION
# =============================================================================

st.sidebar.title("SMD Global Consulting LLC")
st.sidebar.caption(st.session_state.get('user_email', 'Utilisateur'))

# Badge rôle + plan + quota
afficher_badge_role()
afficher_quota_sidebar()

# Indicateur mode démo
if st.session_state.get("role") == "demo":
    st.sidebar.warning("👀 Mode Démonstration")

st.sidebar.divider()

def _aller_a(nom_page):
    """Callback des boutons d'accès rapide : change la page du menu."""
    st.session_state["nav_page"] = nom_page


page = st.sidebar.selectbox(
    "Navigation",
    [
        "🏠 Accueil",
        "🗂 Mes dossiers",
        "─── Analyse & Contrôle ───",
        "🧾 Analyse et comptabilisation de factures",
        "📊 Contrôle de balance",
        "🛡 Loi de Benford",
        "⚠ Alertes & Anomalies",
        "✅ Cohérence des Données",
        "─── États Financiers ───",
        "📈 Compte de Résultat",
        "📊 Bilan Comptable",
        "🔄 Rapprochement Bancaire",
        "📦 Immobilisations",
        "📋 Inventaire & Clôture",
        "📐 Plan de Financement",
        "💹 TFT Trésorerie",
        "📊 Comparatif N/N-1",
        "🧾 Aide TVA CA3/CA12",
        "─── Supervision & Reporting ───",
        "📂 Traitement FEC",
        "📋 Rapport Client",
        "📰 Veille Fiscale",
        "─── Connecteurs ───",
        "🔌 Connecteurs ERP",
        "─── Paramètres ───",
        "👥 Mon cabinet",
        "💳 Tarifs & Abonnement",
        "🔒 Confidentialité & Sécurité",
    ],
    label_visibility="collapsed",
    key="nav_page",
)

# Neutraliser les séparateurs
separateurs = ["─── Analyse & Contrôle ───", "─── États Financiers ───",
               "─── Supervision & Reporting ───", "─── Connecteurs ───",
               "─── Paramètres ───"]
if page in separateurs:
    page = "🏠 Accueil"

# Dossier client en cours : les sauvegardes y sont rangées (hors mode démonstration)
if st.session_state.get("role") != "demo":
    try:
        from utils.database import lister_clients
        _clients = {c[0]: c[1] for c in lister_clients()}
    except Exception:
        _clients = {}
    if st.session_state.get("dossier_id") not in _clients:
        st.session_state["dossier_id"] = 0          # 0 = aucun dossier
    st.sidebar.selectbox("📁 Client sur lequel vous travaillez", [0] + list(_clients), key="dossier_id",
                         format_func=lambda i: _clients.get(i, "Aucun client choisi"),
                         help="Les analyses que vous sauvegardez (bouton 💾 Sauvegarder) sont rangées dans le dossier de "
                              "ce client. Vous les retrouvez dans 🗂 Mes dossiers.")
    st.session_state["dossier_nom"] = _clients.get(st.session_state.get("dossier_id"))
    if not st.session_state["dossier_nom"]:
        st.sidebar.caption("Vos sauvegardes ne seront rangées dans aucun dossier client. "
                           + ("Choisissez un client ci-dessus ou créez-en un." if _clients else "Créez votre premier client :"))

    def _nouveau_client_menu():
        nom = st.session_state.get("menu_nouveau_client", "").strip()
        if not nom:
            st.session_state["menu_client_msg"] = "Saisissez le nom du client."
            return
        from utils.database import creer_client
        cid = creer_client(nom)
        if cid and not isinstance(cid, bool):
            st.session_state["dossier_id"] = cid
            st.session_state["menu_nouveau_client"] = ""
            st.session_state["menu_client_msg"] = None
            st.toast(f"✅ Dossier « {nom} » créé : vos sauvegardes y seront rangées.")
        else:
            st.session_state["menu_client_msg"] = "Création impossible (base de données indisponible). Réessayez."

    with st.sidebar.popover("➕ Nouveau client", width="stretch"):
        st.text_input("Nom du client", key="menu_nouveau_client", placeholder="ex. SARL Martin")
        st.button("Créer le dossier", type="primary", width="stretch", on_click=_nouveau_client_menu,
                  key="menu_btn_client")
        if st.session_state.get("menu_client_msg"):
            st.warning(st.session_state["menu_client_msg"])
        st.caption("SIRET, secteur et contact se complètent dans 🗂 Mes dossiers.")

st.sidebar.divider()

if st.sidebar.button("Se déconnecter", width="stretch"):
    logout()
# =============================================================================
# PAGES / MODULES
# =============================================================================

# -----------------------------------------------------------------------------
# 1. ACCUEIL
# -----------------------------------------------------------------------------

if page == "\U0001f3e0 Accueil":
    from utils.page_accueil import page_accueil
    page_accueil(_aller_a)

elif page == "🗂 Mes dossiers":
    from utils.page_dossiers import page_dossiers
    page_dossiers()

# 2. ANALYSE FACTURE (OCR) - VERSION PROFESSIONNELLE
# -----------------------------------------------------------------------------

elif page == "🧾 Analyse et comptabilisation de factures":
    try:
        from utils.analyse_facture import page_analyse_facture
        page_analyse_facture()
    except ImportError as e:
        st.error(f"Module analyse_facture indisponible : {e}")
elif page == "📊 Contrôle de balance":
    try:
        from utils.audit_balance import page_audit_balance
        page_audit_balance()
    except ImportError as e:
        st.error(f"Module audit_balance indisponible : {e}")
elif page == "📂 Traitement FEC":
    try:
        from utils.fec import page_fec
        page_fec()
    except ImportError as e:
        st.error(f"Module fec indisponible : {e}")
elif page == "🛡 Loi de Benford":
    try:
        from utils.benford_module import page_benford
        page_benford()
    except ImportError as e:
        st.error(f"Module benford_module indisponible : {e}")
elif page == "📈 Compte de Résultat":
    try:
        from utils.compte_resultat import page_compte_resultat
        page_compte_resultat()
    except ImportError as e:
        st.error(f"Module compte_resultat indisponible : {e}")
elif page == "📊 Bilan Comptable":
    try:
        from utils.bilan import page_bilan
        page_bilan()
    except ImportError as e:
        st.error(f"Module bilan indisponible : {e}")
elif page == "🔄 Rapprochement Bancaire":
    try:
        from utils.rapprochement import page_rapprochement
        page_rapprochement()
    except ImportError as e:
        st.error(f"Module rapprochement indisponible : {e}")
elif page == "📦 Immobilisations":
    try:
        from utils.immobilisations import page_immobilisations
        page_immobilisations()
    except ImportError as e:
        st.error(f"Module immobilisations indisponible : {e}")
elif page == "📋 Inventaire & Clôture":
    try:
        from utils.inventaire import page_inventaire
        page_inventaire()
    except ImportError as e:
        st.error(f"Module inventaire indisponible : {e}")
elif page == "📐 Plan de Financement":
    try:
        from utils.plan_financement import page_plan_financement
        page_plan_financement()
    except ImportError as e:
        st.error(f"Module plan_financement indisponible : {e}")

# -----------------------------------------------------------------------------
# 9b. TFT TRESORERIE
# -----------------------------------------------------------------------------

elif page == "💹 TFT Trésorerie":
    try:
        from utils.tft import page_tft
        page_tft()
    except ImportError as e:
        st.error(f"Module TFT indisponible : {e}")

# -----------------------------------------------------------------------------
# 9c. COMPARATIF N/N-1
# -----------------------------------------------------------------------------

elif page == "📊 Comparatif N/N-1":
    try:
        from utils.comparatif import page_comparatif
        page_comparatif()
    except ImportError as e:
        st.error(f"Module Comparatif indisponible : {e}")

# -----------------------------------------------------------------------------
# 9d. AIDE TVA CA3/CA12
# -----------------------------------------------------------------------------

elif page == "🧾 Aide TVA CA3/CA12":
    try:
        from utils.tva import page_tva
        page_tva()
    except ImportError as e:
        st.error(f"Module TVA indisponible : {e}")

# -----------------------------------------------------------------------------
# 9. RAPPORT CLIENT - VERSION PRO AVEC MODE MANUEL
# -----------------------------------------------------------------------------

elif page == "📋 Rapport Client":
    try:
        from utils.rapport_client import page_rapport_client
        page_rapport_client()
    except ImportError as e:
        st.error(f"Module rapport_client indisponible : {e}")
elif page == "⚠ Alertes & Anomalies":
    try:
        from utils.alertes import page_alertes
        page_alertes()
    except ImportError as e:
        st.error(f"Module alertes indisponible : {e}")
elif page == "✅ Cohérence des Données":
    try:
        from utils.coherence import page_coherence
        page_coherence()
    except ImportError as e:
        st.error(f"Module cohérence indisponible : {e}")
elif page == "📰 Veille Fiscale":
    try:
        from utils.veille_fiscale import page_veille_fiscale
        page_veille_fiscale()
    except ImportError as e:
        st.error(f"Module veille_fiscale indisponible : {e}")
elif page == "🔌 Connecteurs ERP":
    from utils.page_connectors import page_connectors
    page_connectors(app_name="pcg")

# 13b. TARIFS & ABONNEMENT
# -----------------------------------------------------------------------------

elif page == "👥 Mon cabinet":
    from utils.page_cabinet import page_cabinet
    page_cabinet()

elif page == "💳 Tarifs & Abonnement":
    from utils.page_tarifs import page_tarifs
    from utils.stripe_billing import gerer_retour_stripe
    gerer_retour_stripe()
    page_tarifs(app_name="pcg")

# 14. CONFIDENTIALITÉ & SÉCURITÉ
# -----------------------------------------------------------------------------

elif page == "🔒 Confidentialité & Sécurité":
    st.title("🔒 Confidentialité & Sécurité")
    st.markdown("**Engagements SMD Global Consulting LLC** envers la protection de vos données")
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.success("### 📂 Fichiers non enregistrés\n\nLes fichiers que vous déposez sont lus en mémoire pour l'analyse "
                   "et ne sont pas enregistrés sur nos serveurs.")
    with col2:
        st.success("### 🗓️ Sauvegardes limitées\n\nSeules les analyses que vous choisissez de sauvegarder sont conservées, "
                   "dans une base hébergée dans l'UE (Irlande), puis supprimées automatiquement après 30 jours.")
    with col3:
        st.info("### 🤖 IA signalée\n\nLes analyses IA sont rédigées par Mistral AI (France) et signalées comme telles. "
                "Avant l'envoi, les identifiants (SIREN, SIRET, n° de TVA, IBAN, e-mails, téléphones, nom de "
                "l'entreprise saisi) sont remplacés par des repères, puis remis en clair dans la réponse. "
                "Les montants et le texte libre sont transmis tels quels : n'y saisissez pas de données "
                "personnelles inutiles. L'utilisation de ces données pour entraîner les modèles de Mistral "
                "est désactivée depuis le 07/10/2026.")
    st.caption("La comptabilisation des factures (comptes PCG, TVA, export FEC) est calculée par des règles, sans IA.")
    st.divider()
    st.markdown("[Conditions générales d'utilisation](?doc=cgu) · "
                "[Politique de confidentialité complète](?doc=confidentialite)")
    st.markdown("### 📋 Politique de Conservation (RGPD)")
    st.info("Les analyses sauvegardées sont automatiquement supprimées après **30 jours**.")
    st.caption("**SMD Global Consulting LLC** — Superviseur IA Comptable © 2026")
