# -*- coding: utf-8 -*- 
"""
Superviseur IA Comptable - SMD Global Consulting LLC
Application complète de supervision comptable augmentée par IA
Auteur: Souleymane Diallo
"""

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
appliquer_theme()

# Initialisation de la base de données
init_db()

# RGPD : suppression automatique des analyses sauvegardées depuis plus de 30 jours (au plus 1 fois / heure)
from utils.database import purger_si_necessaire
purger_si_necessaire()

# =============================================================================
# AUTHENTIFICATION
# =============================================================================

if not is_connecte():
    # Retour Stripe éventuel (upgrade depuis login)
    from utils.stripe_billing import gerer_retour_stripe
    gerer_retour_stripe()

    tab_login, tab_signup = st.tabs(["Se connecter", "Créer un compte"])

    with tab_login:
        col_marque, _, col_form = st.columns([5, 1, 4])
        with col_marque:
            st.markdown(
                "<div class='smd-marque'>SMD Global Consulting LLC</div>"
                "<h1 style='margin:0 0 .75rem'>Superviseur IA Comptable</h1>"
                "<p class='smd-accroche'>Audit et supervision comptable pour les cabinets, "
                "conformes au PCG et aux exigences de la DGFiP.</p>"
                "<ul class='smd-engagements'>"
                "<li>Fichiers non enregistrés <span>: lus en mémoire le temps de l'analyse</span></li>"
                "<li>Sauvegardes limitées <span>: à votre demande, dans l'UE, supprimées après 30 jours</span></li>"
                "<li>IA signalée <span>: tout texte rédigé par l'IA (Mistral AI) est identifié</span></li>"
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

        st.caption("SMD Global Consulting LLC © 2026")

    with tab_signup:
        from utils.page_inscription import page_inscription
        page_inscription(app_name="pcg")

    st.stop()

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
    """Callback des boutons d'acces rapide : change la page du menu."""
    st.session_state["nav_page"] = nom_page


page = st.sidebar.selectbox(
    "Navigation",
    [
        "🏠 Accueil",
        "─── Analyse & Audit ───",
        "🧾 Analyse et comptabilisation de factures",
        "📊 Audit Balance",
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
        "💳 Tarifs & Abonnement",
        "🔒 Confidentialité & Sécurité",
    ],
    label_visibility="collapsed",
    key="nav_page",
)

# Neutraliser les séparateurs
separateurs = ["─── Analyse & Audit ───", "─── États Financiers ───",
               "─── Supervision & Reporting ───", "─── Connecteurs ───",
               "─── Paramètres ───"]
if page in separateurs:
    page = "🏠 Accueil"

st.sidebar.divider()

if st.sidebar.button("Se déconnecter", width="stretch"):
    logout()
# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def is_demo():
    """Vérifie si l'utilisateur est en mode démonstration"""
    return st.session_state.get("role") == "demo"

def banniere_demo():
    """Affiche une bannière demo si applicable"""
    if is_demo():
        st.warning("👀 **Mode Démonstration** — Données fictives uniquement. Sauvegarde désactivée.")

def sauvegarder_si_autorise(type_analyse, resultat):
    """Sauvegarde uniquement si pas en mode démo"""
    if is_demo():
        st.info("💡 Sauvegarde désactivée en mode démonstration.")
    else:
        sauvegarder_analyse(type_analyse=type_analyse, resultat=resultat)

def generer_bouton_word(titre, contenu):
    """Génère un bouton de téléchargement Word sécurisé"""
    try:
        texte_final = extraire_contenu_mistral(contenu)
        buf = export_analyse_word(titre, texte_final)
        st.download_button(
            f"📄 Télécharger {titre}", 
            buf, 
            f"{sanitize_filename(titre)}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            width="stretch"
        )
    except Exception as e:
        st.warning("⚠ Export Word temporairement indisponible. Copiez le contenu manuellement.")

def appel_mistral_securise(prompt, temperature=0.3, label="analyse"):
    """Appel Mistral avec fallback et message utilisateur clair"""
    try:
        result = appel_mistral(prompt, temperature=temperature)
        if result["success"]:
            return result
        else:
            st.warning(f"⚠ L'IA est momentanément indisponible pour {label}. Réessayez dans quelques instants.")
            return {"success": False, "content": "", "error": result.get("error", "")}
    except Exception as e:
        st.warning(f"⚠ Connexion IA interrompue pour {label}. Vérifiez votre connexion.")
        return {"success": False, "content": "", "error": str(e)}
@st.cache_data(show_spinner=False)
def _charger_fichier_bytes(file_bytes: bytes, file_name: str, header: int = 0):
    """Charge un fichier depuis ses bytes (hashable par st.cache_data)."""
    import io
    buf = io.BytesIO(file_bytes)
    try:
        if file_name.endswith('xlsx'):
            return pd.read_excel(buf, header=header), None
        elif file_name.endswith('txt'):
            buf.seek(0)
            return pd.read_csv(buf, sep='|', encoding='utf-8', header=header), None
        else:
            buf.seek(0)
            return pd.read_csv(buf, sep=None, engine='python', header=header), None
    except Exception as e:
        return None, str(e)


def charger_fichier(uploaded_file, header=0):
    """Charge un fichier CSV ou XLSX en DataFrame (cache sur bytes, pas sur UploadedFile)."""
    try:
        file_bytes = uploaded_file.getvalue()
        return _charger_fichier_bytes(file_bytes, uploaded_file.name, header)
    except Exception as e:
        return None, str(e)

# =============================================================================
# PAGES / MODULES
# =============================================================================

# -----------------------------------------------------------------------------
# 1. ACCUEIL
# -----------------------------------------------------------------------------

if page == "\U0001f3e0 Accueil":
    from utils.page_accueil import page_accueil
    page_accueil(_aller_a)

# 2. ANALYSE FACTURE (OCR) - VERSION PROFESSIONNELLE
# -----------------------------------------------------------------------------

elif page == "🧾 Analyse et comptabilisation de factures":
    try:
        from utils.analyse_facture import page_analyse_facture
        page_analyse_facture()
    except ImportError as e:
        st.error(f"Module analyse_facture indisponible : {e}")
elif page == "📊 Audit Balance":
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
        st.error(f"Module coherence indisponible : {e}")
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
                "Les données utiles à l'analyse (par exemple soldes et libellés de comptes) lui sont transmises "
                "sans anonymisation : n'y saisissez pas de données personnelles inutiles.")
    st.caption("La comptabilisation des factures (comptes PCG, TVA, export FEC) est calculée par des règles, sans IA.")
    st.divider()
    st.markdown("### 📋 Politique de Conservation (RGPD)")
    st.info("Les analyses sauvegardées sont automatiquement supprimées après **30 jours**.")
    st.caption("**SMD Global Consulting LLC** — Superviseur IA Comptable © 2026")
