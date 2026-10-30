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
import html
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
    page_title="KontrolIA · SMD Global Consulting LLC", 
    layout="wide", 
    page_icon="static/favicon.png",
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

# Lien « mot de passe oublié » reçu par e-mail : ?reset=<jeton>
_jeton_reset = st.query_params.get("reset")
if _jeton_reset:
    from utils.mot_de_passe_oublie import page_reinitialisation
    page_reinitialisation(_jeton_reset)
    st.stop()

# =============================================================================
# AUTHENTIFICATION
# =============================================================================

if not is_connecte():
    # Retour Stripe éventuel (upgrade depuis login)
    _retour_stripe = st.query_params.get("stripe")
    from utils.stripe_billing import gerer_retour_stripe
    gerer_retour_stripe()

    # Page publique de présentation, sauf lien d'essai (?essai=1), retour Stripe ou visiteur qui l'a déjà quittée
    if not (st.query_params.get("essai") or _retour_stripe or st.session_state.get("vitrine_vue")):
        from utils.page_vitrine import page_vitrine
        page_vitrine()
        st.stop()

    # Lien d'invitation des e-mails de prospection (…/?essai=1) : l'inscription (essai Pro 14 jours) s'ouvre en premier
    if st.query_params.get("essai"):
        st.session_state["ouvrir_inscription"] = True
    # Venant du bouton « Tester gratuitement » : l'onglet d'inscription s'ouvre en premier
    if st.session_state.get("ouvrir_inscription"):
        tab_signup, tab_login = st.tabs(["Créer un compte", "Se connecter"])
    else:
        tab_login, tab_signup = st.tabs(["Se connecter", "Créer un compte"])

    with tab_login:
        col_marque, _, col_form = st.columns([5, 1, 4])
        with col_marque, st.container(key="smd_panneau"):
            st.markdown(
                "<img class='smd-logo' src='app/static/logo_smd.png' alt='SMD Global Consulting LLC'>"
                "<h1 style='margin:0 0 .5rem'>Kontrol<span style='color:#5FB8E6'>IA</span></h1>"
                "<p class='smd-slogan'>« Vous décidez, votre assistant KontrolIA vérifie »</p>"
                "<p class='smd-accroche'>L'assistant des comptables, gestionnaires, DAF et experts-comptables "
                "au quotidien : contrôles, états financiers et TVA selon le PCG et les exigences de la DGFiP.</p>"
                "<ul class='smd-engagements'>"
                "<li>Fichiers non enregistrés <span>: lus en mémoire le temps de l'analyse</span></li>"
                "<li>Sauvegardes limitées <span>: à votre demande, en France (OVH), supprimées après 30 jours</span></li>"
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
                elif st.session_state.get("login_bloque"):
                    st.error("Trop de tentatives de connexion pour cette adresse. Réessayez dans 15 minutes.",
                             icon=":material/lock:")
                else:
                    st.error("Email ou mot de passe incorrect. Vérifiez la saisie ou demandez un accès.")
            from utils.mot_de_passe_oublie import formulaire_demande
            formulaire_demande()

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
        st.button("Découvrir KontrolIA", key="btn_vitrine", icon=":material/arrow_back:",
                  on_click=lambda: st.session_state.update(vitrine_vue=False))

    with tab_signup:
        from utils.page_inscription import page_inscription
        page_inscription(app_name="pcg")

    st.stop()

st.session_state.pop("ouvrir_inscription", None)   # connecté : ordre normal des onglets la prochaine fois

# =============================================================================
# SIDEBAR - NAVIGATION
# =============================================================================

st.logo("static/logo_smd.png", size="large", icon_image="static/logo_smd_globe.png")
st.sidebar.markdown("<div class='smd-produit-menu'>Kontrol<span>IA</span>"
                    "<small>« Vous décidez, votre assistant KontrolIA vérifie »</small></div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='smd-utilisateur'>{html.escape(st.session_state.get('user_email', 'Utilisateur'))}</div>",
                    unsafe_allow_html=True)

# Dernière activité de l'utilisateur (page Supervision), au plus toutes les 5 minutes
from utils.page_supervision import noter_activite
noter_activite()

# Badge rôle + plan + quota
afficher_badge_role()
afficher_quota_sidebar()

# Indicateur mode démo
if st.session_state.get("role") == "demo":
    st.sidebar.markdown("<div class='smd-demo'>Mode démonstration : rien n'est sauvegardé.</div>",
                        unsafe_allow_html=True)

def _aller_a(nom_page):
    """Change la page affichée (menu et boutons d'accès rapide)."""
    st.session_state["nav_page"] = nom_page


# Menu : (identifiant interne de la page, libellé affiché, icône)
MENU = [
    (None, [("🏠 Accueil", "Accueil", ":material/home:"),
            ("🗂 Mes dossiers", "Mes dossiers", ":material/folder_open:")]),
    ("Analyse et contrôle", [
        ("🧾 Analyse et comptabilisation de factures", "Factures", ":material/receipt_long:"),
        ("📊 Contrôle de balance", "Contrôle de balance", ":material/balance:"),
        ("🛡 Loi de Benford", "Loi de Benford", ":material/query_stats:"),
        ("⚠ Alertes & Anomalies", "Alertes et anomalies", ":material/report:"),
        ("✅ Cohérence des Données", "Cohérence des données", ":material/fact_check:")]),
    ("États financiers", [
        ("📈 Compte de Résultat", "Compte de résultat", ":material/trending_up:"),
        ("📊 Bilan Comptable", "Bilan", ":material/account_balance:"),
        ("🔄 Rapprochement Bancaire", "Rapprochement bancaire", ":material/sync_alt:"),
        ("📦 Immobilisations", "Immobilisations", ":material/domain:"),
        ("📋 Inventaire & Clôture", "Inventaire et clôture", ":material/inventory_2:"),
        ("📐 Plan de Financement", "Plan de financement", ":material/savings:"),
        ("💹 TFT Trésorerie", "Flux de trésorerie", ":material/payments:"),
        ("📊 Comparatif N/N-1", "Comparatif N / N-1", ":material/compare_arrows:"),
        ("🧾 Aide TVA CA3/CA12", "TVA CA3 / CA12", ":material/percent:")]),
    ("Supervision et reporting", [
        ("📂 Traitement FEC", "Fichier des écritures (FEC)", ":material/description:"),
        ("📋 Rapport Client", "Rapport client", ":material/summarize:"),
        ("📰 Veille Fiscale", "Veille fiscale", ":material/newspaper:"),
        ("🔌 Connecteurs ERP", "Connecteurs logiciels", ":material/cable:")]),
    ("Cabinet", [
        ("👥 Mon cabinet", "Mon cabinet", ":material/group:"),
        ("💳 Tarifs & Abonnement", "Abonnement", ":material/credit_card:"),
        ("🔒 Confidentialité & Sécurité", "Confidentialité et sécurité", ":material/shield:")]),
]
if st.session_state.get("role") == "admin":   # supervision de la plateforme : administrateur seulement
    MENU.append(("Administration", [("🛰 Supervision", "Supervision", ":material/monitoring:")]))
PAGES = [pid for _, items in MENU for pid, _, _ in items]
if st.session_state.get("nav_page") not in PAGES:
    st.session_state["nav_page"] = "🏠 Accueil"
page = st.session_state["nav_page"]

# Dossier client en cours : les sauvegardes y sont rangées (hors mode démonstration)
if st.session_state.get("role") != "demo":
    try:
        from utils.database import lister_clients
        _clients = {c[0]: c[1] for c in lister_clients()}
    except Exception:
        _clients = {}
    if st.session_state.get("dossier_id") not in _clients:
        st.session_state["dossier_id"] = 0          # 0 = aucun dossier
    st.sidebar.selectbox("Client sur lequel vous travaillez", [0] + list(_clients), key="dossier_id",
                         format_func=lambda i: _clients.get(i, "Aucun client choisi"),
                         help="Les analyses que vous sauvegardez (bouton Sauvegarder) sont rangées dans le dossier de "
                              "ce client. Vous les retrouvez dans Mes dossiers.")
    st.session_state["dossier_nom"] = _clients.get(st.session_state.get("dossier_id"))
    if not st.session_state["dossier_nom"]:
        st.sidebar.caption("Choisissez un client pour y ranger vos sauvegardes." if _clients
                           else "Créez un client pour y ranger vos sauvegardes.")

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
            st.toast(f"Dossier « {nom} » créé : vos sauvegardes y seront rangées.")
        else:
            st.session_state["menu_client_msg"] = "Création impossible (base de données indisponible). Réessayez."

    with st.sidebar.popover("Nouveau client", icon=":material/add:", width="stretch"):
        st.text_input("Nom du client", key="menu_nouveau_client", placeholder="ex. SARL Martin")
        st.button("Créer le dossier", type="primary", width="stretch", on_click=_nouveau_client_menu,
                  key="menu_btn_client")
        if st.session_state.get("menu_client_msg"):
            st.warning(st.session_state["menu_client_msg"])
        st.caption("SIRET, secteur et contact se complètent dans Mes dossiers.")

with st.sidebar.container(key="smd_menu"):
    for _section, _items in MENU:
        if _section:
            st.markdown(f"<div class='smd-section'>{_section}</div>", unsafe_allow_html=True)
        for _pid, _lib, _ico in _items:
            st.button(_lib, icon=_ico, key=f"menu_{PAGES.index(_pid)}", width="stretch",
                      type="primary" if _pid == page else "tertiary", on_click=_aller_a, args=(_pid,))

st.sidebar.divider()

if st.sidebar.button("Se déconnecter", icon=":material/logout:", width="stretch", key="deconnexion"):
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

elif page == "🛰 Supervision":
    from utils.page_supervision import page_supervision
    page_supervision()

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
    st.title("Confidentialité et sécurité")
    st.markdown("**Engagements SMD Global Consulting LLC** envers la protection de vos données")
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.success("### Fichiers non enregistrés\n\nLes fichiers que vous déposez sont lus en mémoire pour l'analyse "
                   "et ne sont pas enregistrés sur nos serveurs.", icon=":material/check_circle:")
    with col2:
        st.success("### Sauvegardes limitées\n\nSeules les analyses que vous choisissez de sauvegarder sont conservées, "
                   "dans une base hébergée en France (OVH, Gravelines), puis supprimées automatiquement après 30 jours.", icon=":material/check_circle:")
    with col3:
        st.info("### IA signalée\n\nLes analyses IA sont rédigées par Mistral AI (France) et signalées comme telles. "
                "Avant l'envoi, les identifiants (SIREN, SIRET, n° de TVA, IBAN, e-mails, téléphones, nom de "
                "l'entreprise saisi) sont remplacés par des repères, puis remis en clair dans la réponse. "
                "Les montants et le texte libre sont transmis tels quels : n'y saisissez pas de données "
                "personnelles inutiles. L'utilisation de ces données pour entraîner les modèles de Mistral "
                "est désactivée depuis le 07/10/2026.", icon=":material/info:")
    st.caption("La comptabilisation des factures (comptes PCG, TVA, export FEC) est calculée par des règles, sans IA.")
    st.divider()
    st.markdown("[Conditions générales d'utilisation](?doc=cgu) · "
                "[Politique de confidentialité complète](?doc=confidentialite)")
    st.markdown("### Politique de conservation (RGPD)")
    st.info("Les analyses sauvegardées sont automatiquement supprimées après **30 jours**. "
            "Les copies de sauvegarde de la base, faites chaque nuit, sont effacées après **15 jours** au plus.")
    st.caption("**KontrolIA** — conçu par SMD Global Consulting LLC © 2026")
