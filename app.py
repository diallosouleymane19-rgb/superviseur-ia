# -*- coding: utf-8 -*-
"""
Superviseur IA Comptable - SMD Consulting
Application complète de supervision comptable augmentée par IA
Auteur: Souleymane Diallo
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Imports des modules utils
from utils.ocr import ocr_image_mistral
from utils.ai import appel_mistral, extraire_contenu_mistral, appel_mistral_vision
from utils.export_word import export_analyse_word
from utils.veille_fiscale import obtenir_veille_fiscale
from utils.database import init_db, sauvegarder_analyse
from utils.fec import valider_fec, analyser_fec
from utils.rendu_financier import afficher_rapport, afficher_synthese_score
from utils.permissions import afficher_badge_role, afficher_quota_sidebar, check_quota, log_user_action
from utils.bilan import generer_bilan
from utils.rapprochement import rapprocher_bancaire
from utils.rapport_client import generer_rapport_client
from utils.alertes import detecter_alertes
from utils.coherence import verifier_coherence
from utils.plan_financement import page_plan_financement
from utils.tft import page_tft
from utils.comparatif import page_comparatif
from utils.tva import page_tva
from utils.benford_module import analyse_benford_complete

# Authentification
from auth import login, logout, is_connecte

# =============================================================================
# CONFIGURATION DE L'APPLICATION
# =============================================================================

st.set_page_config(
    page_title="SMD Consulting - Superviseur IA", 
    layout="wide", 
    page_icon="🔒",
    initial_sidebar_state="expanded"
)

# Initialisation de la base de données
init_db()

# =============================================================================
# AUTHENTIFICATION
# =============================================================================

if not is_connecte():
    # Retour Stripe éventuel (upgrade depuis login)
    from utils.stripe_billing import gerer_retour_stripe
    gerer_retour_stripe()

    tab_login, tab_signup = st.tabs(["🔑 Se connecter", "📝 Créer un compte"])

    with tab_login:
        st.title("🔒 Superviseur IA Comptable")
        st.subheader("Accès réservé aux cabinets clients")

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("---")
            st.markdown("""
            <div style='background:#f0fdf4;padding:12px;border-radius:8px;
                        margin-bottom:10px;font-size:0.85em'>
            ✅ <b>Données anonymisées</b> — SIRET masqués, noms supprimés<br>
            ✅ <b>Non stockées</b> — Aucune conservation après analyse<br>
            ✅ <b>Non utilisées pour entraîner l'IA</b> — Politique Mistral garantie
            </div>
            """, unsafe_allow_html=True)
            st.markdown("---")

            prefill = st.session_state.pop("prefill_email", "")
            email    = st.text_input("📧 Email professionnel",
                                     value=prefill,
                                     placeholder="contact@cabinet.com")
            password = st.text_input("🔑 Mot de passe", type="password")

            if st.button("🚀 Se connecter", type="primary", use_container_width=True):
                if login(email, password):
                    st.success("✅ Connexion réussie !")
                    st.rerun()
                else:
                    st.error("❌ Email ou mot de passe incorrect")

            st.markdown("---")
            st.markdown("##### 🎯 Vous souhaitez tester l'application ?")
            if st.button("👀 Accès Démonstration", use_container_width=True, key="btn_demo"):
                st.session_state.update({
                    "authenticated": True,
                    "user_email":    "demo@smdconsulting.pro",
                    "role":          "demo",
                    "plan":          "free",
                    "nom":           "Démonstration",
                    "login_time":    datetime.now().isoformat(),
                })
                st.rerun()

            st.caption("📧 Demander un accès : contact@smdconsulting.pro")
            st.markdown("---")

        st.divider()
        st.caption("SMD Consulting © 2026 - Comptable IA Augmenté")

    with tab_signup:
        from utils.page_inscription import page_inscription
        page_inscription(app_name="pcg")

    st.stop()

# =============================================================================
# SIDEBAR - NAVIGATION
# =============================================================================

st.sidebar.title("SMD Consulting")
st.sidebar.caption(f"👤 {st.session_state.get('user_email', 'Utilisateur')}")

# Badge rôle + plan + quota
afficher_badge_role()
afficher_quota_sidebar()

# Indicateur mode démo
if st.session_state.get("role") == "demo":
    st.sidebar.warning("👀 Mode Démonstration")

st.sidebar.divider()

page = st.sidebar.selectbox(
    "Navigation",
    [
        "🏠 Accueil",
        "─── Analyse & Audit ───",
        "🧾 Analyse Facture (OCR)",
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
        "─── Paramètres ───",
        "💳 Tarifs & Abonnement",
        "🔒 Confidentialité & Sécurité",
    ],
    label_visibility="collapsed"
)

# Neutraliser les séparateurs
separateurs = ["─── Analyse & Audit ───", "─── États Financiers ───",
               "─── Supervision & Reporting ───", "─── Paramètres ───"]
if page in separateurs:
    page = "🏠 Accueil"

st.sidebar.divider()

if st.sidebar.button("🚪 Déconnexion", use_container_width=True):
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
            f"{titre.replace(' ', '_')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
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
def charger_fichier(uploaded_file, header=0):
    """Charge un fichier CSV ou XLSX en DataFrame"""
    try:
        if uploaded_file.name.endswith('xlsx'):
            return pd.read_excel(uploaded_file, header=header), None
        elif uploaded_file.name.endswith('txt'):
            return pd.read_csv(uploaded_file, sep='|', encoding='utf-8', header=header), None
        else:
            return pd.read_csv(uploaded_file, sep=None, engine='python', header=header), None
    except Exception as e:
        return None, str(e)

# =============================================================================
# PAGES / MODULES
# =============================================================================

# -----------------------------------------------------------------------------
# 1. ACCUEIL
# -----------------------------------------------------------------------------

if page == "\U0001f3e0 Accueil":
    banniere_demo()

    st.markdown("""
    <div style="padding:1.5rem 1rem 1rem 1rem; border-bottom:2px solid #1F4E79; margin-bottom:1.5rem;">
        <h1 style="margin:0; color:#1F4E79; font-size:1.9rem;">Superviseur IA Comptable</h1>
        <p style="margin:0.4rem 0 0 0; color:#555; font-size:0.95rem;">
            SMD Consulting &nbsp;&middot;&nbsp; Audit &amp; Finance augment&eacute;s par l'IA
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("**\U0001f50d Analyse & Audit**")
        st.caption("Factures OCR, Benford, audit balance, alertes anomalies")
    with col2:
        st.markdown("**\U0001f4ca États Financiers**")
        st.caption("Bilan, CdR/SIG, TFT, Plan de Financement, Comparatif N/N-1")
    with col3:
        st.markdown("**\U0001f4e6 Gestion & Clôture**")
        st.caption("Immobilisations, amortissements, provisions, inventaire")
    with col4:
        st.markdown("**\U0001f4c1 Reporting & Fiscal**")
        st.caption("FEC DGFiP, TVA CA3/CA12, rapports clients, veille fiscale")

    st.divider()

    user = st.session_state.get("user_email", "—")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("\U0001f464 Session", user.split("@")[0] if "@" in user else user)
    c2.metric("\U0001f4e6 Modules", "21")
    c3.metric("✅ Statut", "Opérationnel")
    c4.metric("\U0001f512 Données", "Non conservées")

    st.divider()
    st.caption("SMD Consulting © 2026 — PCG France · ANC/CRC 99-02 · Données traitées localement, jamais stockées.")
# -----------------------------------------------------------------------------
# 2. ANALYSE FACTURE (OCR) - VERSION PROFESSIONNELLE
# -----------------------------------------------------------------------------

elif page == "🧾 Analyse Facture (OCR)":
    st.title("🧾 Analyse de Facture")
    st.markdown("**OCR + IA** : Extraction structurée + Conformité + Comptabilisation")
    st.caption("✨ Pour Cabinets et Saisie comptable automatisée")
    
    # Initialisation état
    if 'fact_ocr' not in st.session_state:
        st.session_state.fact_ocr = None
    if 'fact_donnees' not in st.session_state:
        st.session_state.fact_donnees = None
    if 'fact_controles' not in st.session_state:
        st.session_state.fact_controles = None
    if 'fact_ecritures' not in st.session_state:
        st.session_state.fact_ecritures = None
    if 'fact_nom_fichier' not in st.session_state:
        st.session_state.fact_nom_fichier = None
    
    col1, col2 = st.columns([5, 1])
    with col1:
        uploaded_file = st.file_uploader(
            "📎 Déposer une facture (PDF, PNG, JPG)",
            type=["pdf", "png", "jpg", "jpeg"],
            key="facture_uploader"
        )
    with col2:
        st.write("")
        st.write("")
        if st.button("🔄", help="Réinitialiser"):
            st.session_state.fact_ocr = None
            st.session_state.fact_donnees = None
            st.session_state.fact_controles = None
            st.session_state.fact_ecritures = None
            st.session_state.fact_nom_fichier = None
            st.rerun()
    
    if uploaded_file:
        # ✅ CORRECTION CACHE : Réinitialiser si nouveau fichier uploadé
        if st.session_state.get('fact_nom_fichier') != uploaded_file.name:
            st.session_state.fact_ocr = None
            st.session_state.fact_donnees = None
            st.session_state.fact_controles = None
            st.session_state.fact_ecritures = None
            st.session_state['fact_nom_fichier'] = uploaded_file.name

        # Étape 1 : OCR
        if st.session_state.fact_ocr is None:
            with st.spinner("🔍 Extraction OCR en cours..."):
                try:
                    texte, erreur = ocr_image_mistral(uploaded_file)
                    if erreur:
                        st.error(erreur)
                    elif texte:
                        st.session_state.fact_ocr = texte
                        st.rerun()
                    else:
                        st.error("❌ Impossible d'extraire le texte")
                except Exception as e:
                    st.error(f"❌ Erreur OCR : {e}")
        
        if st.session_state.fact_ocr:
            st.success("✅ Texte extrait avec succès !")
            
            with st.expander("📄 Texte brut extrait"):
                st.code(st.session_state.fact_ocr, language="text")
            
            st.divider()
            
            # Étape 2 : Analyse IA structurée
            if st.session_state.fact_donnees is None:
                if st.button("🤖 Analyser avec IA (extraction structurée)", type="primary", use_container_width=True):
                    with st.spinner("🤖 Analyse structurée en cours..."):
                        try:
                            from utils.analyse_facture import extraire_donnees_facture, verifier_conformite_facture, suggerer_comptabilisation
                            
                            result = extraire_donnees_facture(st.session_state.fact_ocr)
                            
                            if result.get('success'):
                                st.session_state.fact_donnees = result['data']
                                st.session_state.fact_controles = verifier_conformite_facture(result['data'])
                                st.session_state.fact_ecritures = suggerer_comptabilisation(result['data'])
                                st.rerun()
                            else:
                                st.error(f"❌ Erreur analyse : {result.get('error')}")
                                if result.get('raw'):
                                    with st.expander("Réponse brute"):
                                        st.code(result['raw'])
                        except Exception as e:
                            st.error(f"❌ Erreur : {e}")
                            import traceback
                            with st.expander("Détails"):
                                st.code(traceback.format_exc())
            
            # Affichage des résultats
            if st.session_state.fact_donnees:
                donnees = st.session_state.fact_donnees
                
                st.markdown("## 📋 Données Extraites")
                
                # Informations générales
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 🏢 Fournisseur")
                    fournisseur = donnees.get('fournisseur', {})
                    st.write(f"**Nom** : {fournisseur.get('nom', 'N/A')}")
                    st.write(f"**SIRET** : {fournisseur.get('siret', 'N/A')}")
                    st.write(f"**TVA Intra** : {fournisseur.get('tva_intra', 'N/A')}")
                    st.write(f"**Adresse** : {fournisseur.get('adresse', 'N/A')}")
                
                with col2:
                    st.markdown("### 👤 Client")
                    client = donnees.get('client', {})
                    st.write(f"**Nom** : {client.get('nom', 'N/A')}")
                    st.write(f"**Adresse** : {client.get('adresse', 'N/A')}")
                
                st.divider()
                
                # Facture
                st.markdown("### 📄 Facture")
                facture = donnees.get('facture', {})
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("N°", facture.get('numero', 'N/A'))
                with col2:
                    st.metric("Date", facture.get('date', 'N/A'))
                with col3:
                    st.metric("Échéance", facture.get('echeance', 'N/A'))
                with col4:
                    st.metric("Paiement", facture.get('mode_paiement', 'N/A'))
                
                st.divider()
                
                # Montants
                st.markdown("### 💰 Montants")
                montants = donnees.get('montants', {})
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total HT", f"{float(montants.get('total_ht', 0)):,.2f} €")
                with col2:
                    st.metric(f"TVA ({montants.get('taux_tva', 20)}%)", f"{float(montants.get('total_tva', 0)):,.2f} €")
                with col3:
                    st.metric("Total TTC", f"{float(montants.get('total_ttc', 0)):,.2f} €")
                
                st.divider()
                
                # Conformité
                if st.session_state.fact_controles:
                    st.markdown("### ✅ Conformité Légale")
                    st.caption("*Article 242 nonies A du CGI*")
                    
                    for ctrl in st.session_state.fact_controles:
                        if ctrl['statut'] == 'OK':
                            st.success(f"✅ {ctrl['mention']}")
                        elif ctrl['statut'] == 'WARNING':
                            st.warning(f"⚠ {ctrl['mention']}")
                        else:
                            st.error(f"❌ {ctrl['mention']}")
                
                st.divider()
                
                # Comptabilisation
                if st.session_state.fact_ecritures:
                    st.markdown("### 📚 Comptabilisation Suggérée")
                    
                    import pandas as pd
                    df_ecritures = pd.DataFrame(st.session_state.fact_ecritures)
                    df_ecritures['debit'] = df_ecritures['debit'].apply(lambda x: f"{x:,.2f} €" if x > 0 else "")
                    df_ecritures['credit'] = df_ecritures['credit'].apply(lambda x: f"{x:,.2f} €" if x > 0 else "")
                    df_ecritures.columns = ['Compte', 'Libellé', 'Débit', 'Crédit']
                    
                    st.dataframe(df_ecritures, use_container_width=True, hide_index=True)
                
                st.divider()
                
                # Export
                from utils.analyse_facture import generer_rapport_facture
                rapport = generer_rapport_facture(donnees, st.session_state.fact_controles, st.session_state.fact_ecritures)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Sauvegarder", use_container_width=True):
                        sauvegarder_si_autorise(type_analyse="Analyse Facture", resultat=rapport)
                        st.success("✅ Sauvegardé !")
                with col2:
                    try:
                        nom_fact = donnees.get('facture', {}).get('numero', 'inconnu')
                        generer_bouton_word(f"Facture_{nom_fact}", rapport)
                    except Exception as e:
                        st.error(f"Erreur : {e}")

# -----------------------------------------------------------------------------
# 3. AUDIT BALANCE - VERSION UNIVERSELLE
# -----------------------------------------------------------------------------

elif page == "📊 Audit Balance":
    st.title("📊 Audit de Balance Comptable")
    st.markdown("**Analyse approfondie** pour Cabinets, DAF et Dirigeants")
    st.caption("✨ Compatible : Sage, Cegid, EBP, Ciel, ACD, Tiime, Pennylane, QuickBooks")
    
    uploaded_file = st.file_uploader(
        "📎 Déposer votre balance (CSV, XLSX)", 
        type=["csv", "xlsx"]
    )
    
    if uploaded_file:
        from utils.audit_balance import auditer_balance, generer_rapport_audit
        from utils.intelligent_parser import parser_balance_intelligent, nettoyer_balance
        
        mode_lecture = st.radio(
            "🔧 Mode de lecture",
            ["🤖 Auto-détection universelle", "📋 Mode manuel"],
            horizontal=True
        )
        
        try:
            if mode_lecture == "🤖 Auto-détection universelle":
                with st.spinner("🤖 Analyse intelligente de la balance..."):
                    df, info = parser_balance_intelligent(uploaded_file)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📊 Format détecté", info['format_detecte'])
                with col2:
                    st.metric("📍 Ligne en-tête", info['ligne_entete'])
                with col3:
                    st.metric("📝 Lignes données", info['nb_lignes_donnees'])
                
                if info['colonnes_manquantes']:
                    st.warning(f"⚠ Colonnes non détectées : {', '.join(info['colonnes_manquantes'])}. Essayez le mode manuel.")
                
                with st.expander("🔍 Détails de la détection", expanded=False):
                    st.write("**Mapping des colonnes :**")
                    for orig, std in info['colonnes_mappees'].items():
                        st.write(f"- `{orig}` → **{std}**")
                
                with st.expander("👀 Aperçu de la balance", expanded=True):
                    st.dataframe(df.head(15), use_container_width=True)
            
            else:
                col1, col2 = st.columns(2)
                with col1:
                    a_un_entete = st.checkbox("✅ Mon fichier a une ligne d'en-tête", value=True)
                with col2:
                    ligne_entete = st.number_input("Ligne d'en-tête", min_value=0, max_value=20, value=0) if a_un_entete else None
                
                if uploaded_file.name.endswith('xlsx'):
                    df = pd.read_excel(uploaded_file, header=ligne_entete if a_un_entete else None)
                else:
                    df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8', header=ligne_entete if a_un_entete else None)
                
                st.success(f"✅ Balance chargée : **{len(df):,} lignes**")
                
                with st.expander("👀 Aperçu de la balance", expanded=True):
                    st.dataframe(df.head(15), use_container_width=True)
                
                st.divider()
                st.markdown("### 🎯 Identification des Colonnes")
                colonnes_disponibles = ["-- Aucune --"] + [str(c) for c in df.columns]
                
                col1, col2 = st.columns(2)
                with col1:
                    col_compte = st.selectbox("🔢 Compte", colonnes_disponibles, index=1 if len(df.columns) > 0 else 0)
                    col_libelle = st.selectbox("📝 Libellé", colonnes_disponibles, index=2 if len(df.columns) > 1 else 0)
                with col2:
                    col_debit = st.selectbox("📥 Débit", colonnes_disponibles, index=3 if len(df.columns) > 2 else 0)
                    col_credit = st.selectbox("📤 Crédit", colonnes_disponibles, index=4 if len(df.columns) > 3 else 0)
                
                renommage = {}
                if col_compte != "-- Aucune --":
                    renommage[col_compte] = 'CompteNum'
                if col_libelle != "-- Aucune --":
                    renommage[col_libelle] = 'CompteLib'
                if col_debit != "-- Aucune --":
                    renommage[col_debit] = 'Debit'
                if col_credit != "-- Aucune --":
                    renommage[col_credit] = 'Credit'
                
                df = df.rename(columns=renommage)
            
            st.divider()
            
            col1, col2 = st.columns(2)
            with col1:
                nom_entreprise = st.text_input("🏢 Nom de l'entreprise", value="Entreprise")
            with col2:
                exercice = st.text_input("📅 Exercice", value=str(datetime.now().year))
            
            if st.button("🔍 Lancer l'audit professionnel", type="primary", use_container_width=True):
                with st.spinner("Audit en cours..."):
                    audit = auditer_balance(df)

                    afficher_synthese_score(
                        score=audit['score_qualite'],
                        niveau=audit['niveau'],
                        kpis=audit['kpis'],
                        controles=audit['controles'],
                        anomalies=audit['anomalies'],
                        recommandations=audit['recommandations'],
                        devise="€"
                    )

                    st.divider()
                    rapport = generer_rapport_audit(audit, nom_entreprise)
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💾 Sauvegarder", use_container_width=True):
                            sauvegarder_si_autorise(type_analyse="Audit Balance", resultat=rapport)
                            st.success("✅ Sauvegardé !")
                    with col2:
                        try:
                            generer_bouton_word(f"Audit_Balance_{nom_entreprise}", rapport)
                        except Exception as e:
                            st.error(f"Erreur : {e}")
                            
        except Exception as e:
            st.error(f"❌ Erreur : {str(e)}")
            import traceback
            with st.expander("Détails techniques"):
                st.code(traceback.format_exc())

# -----------------------------------------------------------------------------
# 4. TRAITEMENT FEC - VERSION PROFESSIONNELLE CABINET
# -----------------------------------------------------------------------------

elif page == "📂 Traitement FEC":
    st.title("📂 Traitement FEC - Audit Conformité DGFiP")
    st.markdown("**Validation et analyse approfondie** des Fichiers des Écritures Comptables (Article L.47 A du LPF)")
    
    uploaded_file = st.file_uploader(
        "📎 Déposer votre fichier FEC", 
        type=["txt", "csv"],
        help="Format pipe (|) ou tabulation, encodage UTF-8 ou ISO-8859-1"
    )
    
    if uploaded_file:
        from utils.fec import lire_fec, valider_fec, analyser_fec, detecter_anomalies_fec
        
        with st.spinner("📖 Lecture du FEC..."):
            df, sep, enc = lire_fec(uploaded_file)
        
        if df is None:
            st.error("❌ Impossible de lire le FEC. Vérifiez le format (séparateur pipe | ou tabulation).")
        else:
            st.success(f"✅ FEC chargé : **{len(df):,} écritures** | Séparateur : `{sep}` | Encodage : `{enc}`")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📝 Écritures", f"{len(df):,}")
            with col2:
                if 'EcritureNum' in df.columns:
                    st.metric("📄 Pièces", f"{df['EcritureNum'].nunique():,}")
            with col3:
                if 'CompteNum' in df.columns:
                    st.metric("🔢 Comptes", f"{df['CompteNum'].nunique()}")
            with col4:
                if 'JournalCode' in df.columns:
                    st.metric("📚 Journaux", f"{df['JournalCode'].nunique()}")
            
            with st.expander("👀 Aperçu des données (20 premières lignes)"):
                st.dataframe(df.head(20), use_container_width=True)
            
            st.divider()
            
            if st.button("🛡 Lancer la validation DGFiP complète", type="primary", use_container_width=True):
                with st.spinner("Validation en cours selon Article A.47 A-1 du LPF..."):
                    resultats = valider_fec(df)
                    
                    meta = resultats.pop('_meta', {})
                    score = meta.get('score_conformite', 0)
                    niveau = meta.get('niveau', 'Inconnu')
                    
                    st.markdown("## 🎯 Score de Conformité DGFiP")
                    
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if score >= 90:
                            st.success(f"### {niveau} : {score}% ✅")
                        elif score >= 75:
                            st.info(f"### {niveau} : {score}% ℹ")
                        elif score >= 50:
                            st.warning(f"### {niveau} : {score}% ⚠")
                        else:
                            st.error(f"### {niveau} : {score}% ❌")
                        
                        st.progress(min(int(score), 100))
                        st.caption(f"Points obtenus : {meta.get('points', 0)} / {meta.get('points_max', 100)}")
                    
                    st.divider()
                    
                    st.markdown("## 📋 Détail des Contrôles")
                    
                    for verif, status in resultats.items():
                        if status["valide"]:
                            st.success(f"✅ **{verif}** : {status.get('message', 'Conforme')}")
                        else:
                            st.error(f"❌ **{verif}** : {status.get('message', '')}")
                    
                    st.divider()
                    
                    st.markdown("## 🔍 Analyse Approfondie")
                    analyse = analyser_fec(df)
                    afficher_rapport(analyse, afficher_kpis_auto=True, afficher_alertes_auto=True, afficher_tables_auto=True)
                    
                    st.divider()
                    
                    st.markdown("## ⚠ Détection d'Anomalies")
                    anomalies = detecter_anomalies_fec(df)
                    
                    if anomalies:
                        col1, col2, col3 = st.columns(3)
                        nb_elevees = len([a for a in anomalies if a['gravite'] == 'Elevee'])
                        nb_moyennes = len([a for a in anomalies if a['gravite'] == 'Moyenne'])
                        nb_faibles = len([a for a in anomalies if a['gravite'] == 'Faible'])
                        
                        with col1:
                            st.metric("🔴 Élevées", nb_elevees)
                        with col2:
                            st.metric("🟡 Moyennes", nb_moyennes)
                        with col3:
                            st.metric("🔵 Faibles", nb_faibles)
                        
                        for anomalie in anomalies:
                            if anomalie['gravite'] == 'Elevee':
                                st.error(f"🔴 **{anomalie['type']}** ({anomalie['count']}) : {anomalie['description']}")
                            elif anomalie['gravite'] == 'Moyenne':
                                st.warning(f"🟡 **{anomalie['type']}** ({anomalie['count']}) : {anomalie['description']}")
                            else:
                                st.info(f"🔵 **{anomalie['type']}** ({anomalie['count']}) : {anomalie['description']}")
                    else:
                        st.success("✅ Aucune anomalie majeure détectée")
                    
                    st.divider()
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💾 Sauvegarder le rapport", use_container_width=True):
                            sauvegarder_si_autorise(
                                type_analyse="Audit FEC", 
                                resultat=f"Score: {score}% - {analyse}"
                            )
                            st.success("✅ Rapport sauvegardé !")
                    
                    with col2:
                        rapport_complet = f"""# RAPPORT D'AUDIT FEC

## Score de Conformité DGFiP : {score}% ({niveau})

{analyse}

## Anomalies Détectées
{chr(10).join([f"- {a['type']} ({a['gravite']}) : {a['description']}" for a in anomalies]) if anomalies else "Aucune anomalie majeure"}

---
*Rapport généré par SMD Consulting - Superviseur IA Comptable*
"""
                        try:
                            generer_bouton_word("Rapport_Audit_FEC", rapport_complet)
                        except Exception as e:
                            st.error(f"Erreur export : {e}")


# -----------------------------------------------------------------------------
# 5. LOI DE BENFORD - VERSION PROFESSIONNELLE CABINET D'AUDIT
# -----------------------------------------------------------------------------

elif page == "🛡 Loi de Benford":
    st.title("🛡 Audit de Fraude - Loi de Benford")
    st.markdown("**Détection statistique** d'anomalies et manipulations de données")
    st.caption("✨ Méthode utilisée par les cabinets d'audit, IRS, CAC pour la détection de fraude")
    
    with st.expander("ℹ Comment ça marche ?"):
        st.markdown("""
        **La Loi de Benford** (1938) stipule que dans les données numériques naturelles, 
        le **chiffre 1** apparaît comme premier chiffre dans **30%** des cas, 
        le 2 dans 17,6%, le 3 dans 12,5%, etc.
        
        ⚠ **Si vos données ne suivent pas cette distribution**, cela peut indiquer :
        - Manipulation manuelle des chiffres
        - Erreurs de saisie systématiques
        - Seuils d'autorisation contournés
        - **Fraude potentielle**
        
        **Indicateurs analysés** :
        - 📊 **MAD** : Écart moyen absolu (référence Mark Nigrini)
        - 📈 **Chi-carré** : Test statistique de conformité
        - 🎯 **Z-score** par chiffre : détection des anomalies à 99% de confiance
        """)
    
    uploaded_file = st.file_uploader(
        "📎 Données comptables (CSV, XLSX)",
        type=["csv", "xlsx"],
        help="FEC, balance, ou tout fichier avec une colonne de montants"
    )
    
    if uploaded_file:
        df, erreur = charger_fichier(uploaded_file)
        if erreur:
            st.error(f"❌ Erreur lecture fichier : {erreur}")
            st.stop()
        
        st.success(f"✅ Fichier chargé : **{len(df):,} lignes**")
        
        with st.expander("👀 Aperçu des données"):
            st.dataframe(df.head(10), use_container_width=True)
        
        colonnes_num = []
        for col in df.columns:
            try:
                test = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
                if test.notna().sum() > len(df) * 0.5:
                    colonnes_num.append(col)
            except:
                pass
        
        if colonnes_num:
            col_choix = st.selectbox(
                "🔢 Sélectionnez la colonne des montants",
                colonnes_num,
                help="Colonnes numériques détectées automatiquement"
            )
        else:
            col_choix = st.selectbox(
                "🔢 Sélectionnez la colonne des montants",
                df.columns
            )
        
        if st.button("🔍 Lancer l'audit Benford", type="primary", use_container_width=True):
            with st.spinner("Analyse statistique en cours..."):
                try:
                    fig, rapport, score_risque = analyse_benford_complete(df, col_choix)
                    
                    st.markdown("## 🎯 Score de Risque")
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if score_risque == "Faible":
                            st.success(f"### ✅ Risque {score_risque}")
                            st.info("**Conformité Benford** - Pas d'anomalie statistique majeure")
                        elif score_risque == "Modere":
                            st.warning(f"### ⚠ Risque {score_risque}")
                            st.warning("**Écarts détectés** - Investigation recommandée")
                        else:
                            st.error(f"### 🚨 Risque {score_risque}")
                            st.error("**Anomalies significatives** - Audit approfondi nécessaire")
                    
                    st.divider()
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    st.divider()
                    afficher_rapport(rapport, titre="Analyse Statistique Benford", afficher_kpis_auto=True, afficher_alertes_auto=True, compact=True)
                    st.divider()
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💾 Sauvegarder", use_container_width=True):
                            sauvegarder_si_autorise(type_analyse="Loi de Benford", resultat=rapport)
                            st.success("✅ Sauvegardé !")
                    with col2:
                        try:
                            generer_bouton_word("Audit_Benford", rapport)
                        except Exception as e:
                            st.error(f"Erreur : {e}")
                            
                except Exception as e:
                    st.error(f"❌ Erreur : {str(e)}")
                    import traceback
                    with st.expander("Détails techniques"):
                        st.code(traceback.format_exc())
# -----------------------------------------------------------------------------
# 6. COMPTE DE RÉSULTAT - VERSION PROFESSIONNELLE CABINET
# -----------------------------------------------------------------------------

elif page == "📈 Compte de Résultat":
    st.title("📈 Compte de Résultat")
    st.markdown("**Calcul automatique des SIG** (Soldes Intermédiaires de Gestion) selon PCG")
    st.caption("✨ Pour Cabinets, DAF et Dirigeants - Compatible toutes balances")
    
    uploaded_file = st.file_uploader(
        "📎 Déposer votre balance ou FEC",
        type=["csv", "xlsx", "txt"],
        help="La balance doit contenir les comptes des classes 6 (charges) et 7 (produits)"
    )
    
    if uploaded_file:
        from utils.compte_resultat import calculer_compte_resultat, generer_rapport_compte_resultat
        from utils.intelligent_parser import parser_balance_intelligent
        
        try:
            with st.spinner("🤖 Analyse de la balance..."):
                if uploaded_file.name.endswith('xlsx') or uploaded_file.name.endswith('csv'):
                    df, info = parser_balance_intelligent(uploaded_file)
                    st.success(f"✅ Format détecté : **{info['format_detecte']}** | **{len(df):,} comptes**")
                else:
                    df, erreur = charger_fichier(uploaded_file)
                    if erreur:
                        st.error(f"❌ Erreur : {erreur}")
                        st.stop()
                    st.success(f"✅ FEC chargé : **{len(df):,} lignes**")
            
            st.divider()
            col1, col2, col3 = st.columns(3)
            with col1:
                nom_entreprise = st.text_input("🏢 Nom de l'entreprise", value="Entreprise")
            with col2:
                exercice = st.text_input("📅 Exercice", value=str(datetime.now().year))
            with col3:
                type_entreprise = st.selectbox(
                    "🏭 Type d'entreprise",
                    ["Mixte", "Commerciale", "Industrielle", "Services"]
                )
            
            if st.button("📊 Générer le Compte de Résultat", type="primary", use_container_width=True):
                with st.spinner("Calcul des SIG en cours..."):
                    resultat = calculer_compte_resultat(df, type_entreprise)
                    
                    if 'erreur' in resultat:
                        st.error(f"❌ {resultat['erreur']}")
                    else:
                        st.markdown("## 📊 Soldes Intermédiaires de Gestion")
                        st.caption(f"{nom_entreprise} - Exercice {exercice}")
                        
                        sig = resultat['sig']
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            _ca = sig.get("Chiffre d'affaires", 0)
                            st.metric("💰 CA", f"{_ca:,.0f} €")
                        with col2:
                            st.metric("⚙ VA", f"{sig['Valeur ajoutée (VA)']:,.0f} €")
                        with col3:
                            _ebe = sig.get("Excedent Brut d'Exploitation (EBE)", 0)
                            st.metric("📈 EBE", f"{_ebe:,.0f} €")
                        with col4:
                            rn = sig['Resultat net']
                            st.metric("🎯 Résultat Net", f"{rn:,.0f} €",
                                     delta="Bénéfice" if rn > 0 else "Déficit",
                                     delta_color="normal" if rn > 0 else "inverse")
                        
                        st.divider()
                        st.markdown("### 📋 Détail des Soldes Intermédiaires")
                        df_sig = pd.DataFrame([
                            {'Indicateur': nom, 'Montant (€)': f"{val:,.2f}"} 
                            for nom, val in sig.items()
                        ])
                        st.dataframe(df_sig, use_container_width=True, hide_index=True)
                        st.bar_chart(pd.DataFrame([
                            {'Indicateur': nom, 'Montant': val} 
                            for nom, val in sig.items()
                        ]).set_index('Indicateur'))
                        
                        st.divider()
                        if resultat['ratios']:
                            st.markdown("## 📈 Ratios de Performance")
                            ratios = resultat['ratios']
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                if 'Taux de valeur ajoutee (%)' in ratios:
                                    st.metric("Taux VA", f"{ratios['Taux de valeur ajoutee (%)']:.1f}%")
                            with col2:
                                if 'Taux de marge brute - EBE (%)' in ratios:
                                    st.metric("Marge EBE", f"{ratios['Taux de marge brute - EBE (%)']:.1f}%")
                            with col3:
                                if 'Taux de rentabilite exploitation (%)' in ratios:
                                    st.metric("Rentab. Exploit.", f"{ratios['Taux de rentabilite exploitation (%)']:.1f}%")
                            with col4:
                                if 'Taux de rentabilite nette (%)' in ratios:
                                    st.metric("Rentab. Nette", f"{ratios['Taux de rentabilite nette (%)']:.1f}%")
                        
                        st.divider()
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("### 💰 PRODUITS")
                            st.dataframe(pd.DataFrame([
                                {'Rubrique': k, 'Montant (€)': f"{v:,.2f}"} 
                                for k, v in resultat['produits'].items() if v != 0
                            ]), use_container_width=True, hide_index=True)
                        with col2:
                            st.markdown("### 💸 CHARGES")
                            st.dataframe(pd.DataFrame([
                                {'Rubrique': k, 'Montant (€)': f"{v:,.2f}"} 
                                for k, v in resultat['charges'].items() if v != 0
                            ]), use_container_width=True, hide_index=True)
                        
                        st.divider()
                        if resultat['analyse']:
                            st.markdown("## 💡 Analyse Cabinet")
                            for item in resultat['analyse']:
                                if item['type'] == 'OK':
                                    st.success(f"✅ {item['message']}")
                                elif item['type'] == 'WARNING':
                                    st.warning(f"⚠ {item['message']}")
                                else:
                                    st.error(f"🔴 {item['message']}")
                        
                        st.divider()
                        rapport = generer_rapport_compte_resultat(resultat, nom_entreprise, exercice)
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("💾 Sauvegarder", use_container_width=True):
                                sauvegarder_si_autorise(type_analyse="Compte de Résultat", resultat=rapport)
                                st.success("✅ Sauvegardé !")
                        with col2:
                            try:
                                generer_bouton_word(f"Compte_Resultat_{nom_entreprise}", rapport)
                            except Exception as e:
                                st.error(f"Erreur : {e}")
                                
        except Exception as e:
            st.error(f"❌ Erreur : {str(e)}")
            import traceback
            with st.expander("Détails techniques"):
                st.code(traceback.format_exc())
# -----------------------------------------------------------------------------
# 7. BILAN COMPTABLE - VERSION PROFESSIONNELLE CABINET
# -----------------------------------------------------------------------------

elif page == "📊 Bilan Comptable":
    st.title("📊 Bilan Comptable")
    st.markdown("**Vision patrimoniale** avec ratios financiers selon PCG")
    st.caption("✨ Pour Cabinets, DAF et Dirigeants - FDR, BFR, Trésorerie nette")
    
    uploaded_file = st.file_uploader(
        "📎 Déposer votre balance ou FEC",
        type=["csv", "xlsx", "txt"]
    )
    
    if uploaded_file:
        from utils.bilan import calculer_bilan, generer_rapport_bilan
        from utils.intelligent_parser import parser_balance_intelligent
        
        try:
            with st.spinner("🤖 Analyse..."):
                if uploaded_file.name.endswith('xlsx') or uploaded_file.name.endswith('csv'):
                    df, info = parser_balance_intelligent(uploaded_file)
                    st.success(f"✅ Format : **{info['format_detecte']}** | **{len(df):,} comptes**")
                else:
                    df, erreur = charger_fichier(uploaded_file)
                    if erreur:
                        st.error(f"❌ Erreur : {erreur}")
                        st.stop()
                    st.success(f"✅ FEC chargé : **{len(df):,} lignes**")
            
            st.divider()
            col1, col2, col3 = st.columns(3)
            with col1:
                nom_entreprise = st.text_input("🏢 Entreprise", value="Entreprise")
            with col2:
                exercice = st.text_input("📅 Exercice", value=str(datetime.now().year))
            with col3:
                date_cloture = st.date_input("📆 Date de clôture")
            
            if st.button("📊 Générer le Bilan", type="primary", use_container_width=True):
                with st.spinner("Calcul en cours..."):
                    bilan = calculer_bilan(df, str(date_cloture))
                    
                    if 'erreur' in bilan:
                        st.error(f"❌ {bilan['erreur']}")
                    else:
                        st.markdown(f"## 💼 Bilan au {date_cloture}")
                        st.caption(f"{nom_entreprise} - Exercice {exercice}")
                        
                        totaux = bilan['totaux']
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("📦 Actif", f"{totaux['total_actif']:,.0f} €")
                        with col2:
                            st.metric("💼 Passif", f"{totaux['total_passif']:,.0f} €")
                        with col3:
                            st.metric("🏦 Capitaux", f"{totaux['capitaux_propres']:,.0f} €")
                        with col4:
                            ecart = totaux['ecart']
                            st.metric("⚖ Écart", f"{ecart:,.2f} €")
                        
                        if ecart < 1:
                            st.success("✅ Bilan équilibré")
                        else:
                            st.warning(f"⚠ Bilan déséquilibré de {ecart:,.2f} €")
                        
                        st.divider()
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("### 📦 ACTIF")
                            st.dataframe(pd.DataFrame([
                                {'Poste': k, 'Montant (€)': f"{v:,.2f}"} 
                                for k, v in bilan['actif'].items() if v != 0
                            ]), use_container_width=True, hide_index=True)
                        with col2:
                            st.markdown("### 💼 PASSIF")
                            st.dataframe(pd.DataFrame([
                                {'Poste': k, 'Montant (€)': f"{v:,.2f}"} 
                                for k, v in bilan['passif'].items() if v != 0
                            ]), use_container_width=True, hide_index=True)
                        
                        st.divider()
                        if bilan['ratios']:
                            st.markdown("## 📈 Ratios Financiers")
                            ratios = bilan['ratios']
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Autonomie", f"{ratios['Autonomie financiere (%)']:.1f}%")
                            with col2:
                                st.metric("FDR", f"{ratios['Fonds de roulement FDR']:,.0f} €")
                            with col3:
                                st.metric("Trésorerie nette", f"{ratios['Tresorerie nette']:,.0f} €")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Endettement", f"{ratios['Endettement (%)']:.1f}%")
                            with col2:
                                st.metric("BFR", f"{ratios['Besoin FDR BFR']:,.0f} €")
                            with col3:
                                st.metric("Liquidité", f"{ratios['Liquidite generale (%)']:.1f}%")
                        
                        st.divider()
                        if bilan['analyse']:
                            st.markdown("## 💡 Analyse Cabinet")
                            for item in bilan['analyse']:
                                if item['type'] == 'OK':
                                    st.success(f"✅ {item['message']}")
                                elif item['type'] == 'WARNING':
                                    st.warning(f"⚠ {item['message']}")
                                else:
                                    st.error(f"🔴 {item['message']}")
                        
                        st.divider()
                        rapport = generer_rapport_bilan(bilan, nom_entreprise, exercice)
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("💾 Sauvegarder", use_container_width=True):
                                sauvegarder_si_autorise(type_analyse="Bilan", resultat=rapport)
                                st.success("✅ Sauvegardé !")
                        with col2:
                            try:
                                generer_bouton_word(f"Bilan_{nom_entreprise}", rapport)
                            except Exception as e:
                                st.error(f"Erreur : {e}")
                                
        except Exception as e:
            st.error(f"❌ Erreur : {str(e)}")
            import traceback
            with st.expander("Détails techniques"):
                st.code(traceback.format_exc())
# -----------------------------------------------------------------------------
# 8. RAPPROCHEMENT BANCAIRE - VERSION PROFESSIONNELLE
# -----------------------------------------------------------------------------

elif page == "🔄 Rapprochement Bancaire":
    st.title("🔄 Rapprochement Bancaire")
    st.markdown("**Matching intelligent** entre relevé bancaire et écritures comptables")
    st.caption("✨ Matching automatique par montant + date + libellé")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📥 Relevé Bancaire")
        releve = st.file_uploader(
            "Fichier relevé (CSV, XLSX)",
            type=["csv", "xlsx"],
            key="releve",
            help="Colonnes attendues : Date, Libellé, Montant"
        )
    
    with col2:
        st.markdown("### 📚 Écritures Comptables")
        ecritures = st.file_uploader(
            "Fichier écritures (CSV, XLSX)",
            type=["csv", "xlsx"],
            key="ecritures",
            help="Colonnes attendues : Date, Libellé, Débit, Crédit"
        )
    
    if releve and ecritures:
        from utils.rapprochement import rapprocher_bancaire, generer_rapport_rapprochement
        
        try:
            df_releve = pd.read_excel(releve) if releve.name.endswith('xlsx') else pd.read_csv(releve, sep=None, engine='python')
            df_ecritures = pd.read_excel(ecritures) if ecritures.name.endswith('xlsx') else pd.read_csv(ecritures, sep=None, engine='python')
            
            st.success(f"✅ Relevé : **{len(df_releve)} opérations** | Écritures : **{len(df_ecritures)} lignes**")
            
            with st.expander("👀 Aperçu des fichiers"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Relevé bancaire**")
                    st.dataframe(df_releve.head(5), use_container_width=True)
                with col2:
                    st.markdown("**Écritures comptables**")
                    st.dataframe(df_ecritures.head(5), use_container_width=True)
            
            st.divider()
            
            col1, col2 = st.columns(2)
            with col1:
                nom_compte = st.text_input("🏦 Nom du compte", value="Compte bancaire principal")
            with col2:
                tolerance = st.slider("⏱ Tolérance jours", 0, 10, 3,
                                     help="Écart maximum entre date relevé et écriture")
            
            if st.button("🔄 Lancer le rapprochement", type="primary", use_container_width=True):
                with st.spinner("Matching intelligent en cours..."):
                    resultats = rapprocher_bancaire(df_releve, df_ecritures, tolerance_jours=tolerance)
                    
                    st.markdown("## 📊 Résultats du Rapprochement")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("✅ Rapprochés", resultats['nb_rapproches'])
                    with col2:
                        st.metric("❌ Non rapp. relevé", resultats['nb_non_rapproches_releve'])
                    with col3:
                        st.metric("❌ Non rapp. écritures", resultats['nb_non_rapproches_ecritures'])
                    with col4:
                        taux = resultats['taux_rapprochement']
                        st.metric("📈 Taux", f"{taux:.1f}%",
                                 delta="Excellent" if taux >= 90 else "Bon" if taux >= 70 else "À vérifier",
                                 delta_color="normal" if taux >= 70 else "inverse")
                    
                    st.progress(min(int(taux), 100))
                    
                    if taux >= 90:
                        st.success("✅ **Excellent rapprochement** - Quasi-complet")
                    elif taux >= 70:
                        st.info("ℹ **Bon rapprochement** - Satisfaisant")
                    elif taux >= 50:
                        st.warning("⚠ **Rapprochement moyen** - Investigations nécessaires")
                    else:
                        st.error("🚨 **Rapprochement faible** - Anomalies importantes")
                    
                    st.divider()
                    
                    if not resultats['rapproches'].empty:
                        with st.expander(f"✅ Opérations rapprochées ({resultats['nb_rapproches']})"):
                            st.dataframe(resultats['rapproches'], use_container_width=True, hide_index=True)
                    
                    if not resultats['non_rapproches_releve'].empty:
                        with st.expander(f"❌ Relevé non rapproché ({resultats['nb_non_rapproches_releve']})", expanded=True):
                            st.warning("Opérations bancaires sans contrepartie comptable")
                            st.dataframe(resultats['non_rapproches_releve'], use_container_width=True, hide_index=True)
                    
                    if not resultats['non_rapproches_ecritures'].empty:
                        with st.expander(f"❌ Écritures non rapprochées ({resultats['nb_non_rapproches_ecritures']})", expanded=True):
                            st.warning("Écritures sans contrepartie bancaire")
                            st.dataframe(resultats['non_rapproches_ecritures'], use_container_width=True, hide_index=True)
                    
                    st.divider()
                    
                    rapport = generer_rapport_rapprochement(resultats, nom_compte)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💾 Sauvegarder", use_container_width=True):
                            sauvegarder_si_autorise(type_analyse="Rapprochement Bancaire", resultat=rapport)
                            st.success("✅ Sauvegardé !")
                    with col2:
                        try:
                            generer_bouton_word(f"Rapprochement_{nom_compte}", rapport)
                        except Exception as e:
                            st.error(f"Erreur : {e}")
                    
        except Exception as e:
            st.error(f"❌ Erreur : {str(e)}")
            import traceback
            with st.expander("Détails techniques"):
                st.code(traceback.format_exc())
# -----------------------------------------------------------------------------
# IMMOBILISATIONS - AMORTISSEMENTS & CESSIONS
# -----------------------------------------------------------------------------

elif page == "📦 Immobilisations":
    st.title("📦 Gestion des Immobilisations")
    st.markdown("**Amortissements, Cessions et Plan d'investissement**")
    st.caption("✨ Linéaire, Dégressif, Plus/Moins-value de cession")

    from utils.immobilisations import (
        calculer_amortissement_lineaire,
        calculer_amortissement_degressif,
        calculer_cession,
        generer_rapport_immobilisation
    )

    onglet1, onglet2, onglet3 = st.tabs([
        "📋 Tableau d'amortissement",
        "🔄 Cession / Sortie",
        "📊 Plan d'investissement"
    ])

    # ── ONGLET 1 : TABLEAU D'AMORTISSEMENT ──
    with onglet1:
        st.markdown("### 📋 Tableau d'amortissement")

        col1, col2 = st.columns(2)
        with col1:
            nom_bien = st.text_input("🏷 Désignation du bien", placeholder="Ex: Véhicule utilitaire")
            valeur_origine = st.number_input("💰 Valeur d'origine (€)", min_value=0.0, value=10000.0, step=100.0)
            duree_ans = st.number_input("⏱ Durée d'amortissement (ans)", min_value=1, max_value=50, value=5)
        with col2:
            date_acquisition = st.date_input("📅 Date d'acquisition")
            mode = st.selectbox("⚙ Mode d'amortissement", ["Linéaire", "Dégressif"])
            categorie = st.selectbox("🏭 Catégorie", [
                "Matériel et outillage (5 ans)",
                "Véhicules (4-5 ans)",
                "Mobilier (10 ans)",
                "Matériel informatique (3 ans)",
                "Constructions (20-50 ans)",
                "Agencements (10 ans)",
                "Autre"
            ])

        if st.button("📊 Générer le tableau", type="primary", use_container_width=True):
            if not nom_bien:
                st.error("⚠ Veuillez renseigner la désignation du bien")
            else:
                with st.spinner("Calcul en cours..."):
                    from datetime import datetime
                    date_acq = datetime.combine(date_acquisition, datetime.min.time())

                    if mode == "Linéaire":
                        tableau = calculer_amortissement_lineaire(valeur_origine, duree_ans, date_acq)
                    else:
                        tableau = calculer_amortissement_degressif(valeur_origine, duree_ans, date_acq)

                    st.markdown(f"## 📋 {nom_bien} — Amortissement {mode}")

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("💰 Valeur origine", f"{valeur_origine:,.2f} €")
                    with col2:
                        st.metric("⏱ Durée", f"{duree_ans} ans")
                    with col3:
                        taux = 100 / duree_ans
                        st.metric("📊 Taux", f"{taux:.2f}%")
                    with col4:
                        dotation = tableau['Dotation (€)'].iloc[0]
                        st.metric("📅 Dotation/an", f"{dotation:,.2f} €")

                    st.divider()
                    st.dataframe(tableau, use_container_width=True, hide_index=True)

                    # Graphique VNC
                    st.markdown("### 📈 Évolution de la VNC")
                    col_vnc = 'VNC (€)' if 'VNC (€)' in tableau.columns else 'VNC Fin (€)'
                    st.line_chart(tableau.set_index('Année')[col_vnc])

                    st.divider()
                    
                    # Écritures comptables
                    st.markdown("### 📚 Écritures Comptables d'Amortissement")
                    st.caption("Compte 6811 — Dotations aux amortissements / 28xx — Amortissements")
                    
                    from utils.immobilisations import generer_ecritures_amortissement
                    df_ecritures = generer_ecritures_amortissement(nom_bien, tableau)
                    
                    annee_courante = datetime.now().year
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        dotation_courante = df_ecritures[
                            df_ecritures['Année'] == annee_courante
                        ]['Débit (€)'].sum()
                        st.metric("📅 Dotation exercice en cours", f"{dotation_courante:,.2f} €")
                    with col2:
                        total_amorti = df_ecritures[
                            df_ecritures['Statut'].str.contains('Passé|cours', na=False)
                        ]['Débit (€)'].sum()
                        st.metric("📉 Total amorti à ce jour", f"{total_amorti:,.2f} €")
                    with col3:
                        vnc_col = 'VNC (€)' if 'VNC (€)' in tableau.columns else 'VNC Fin (€)'
                        vnc_actuelle = tableau[tableau['Année'] == annee_courante][vnc_col].values
                        vnc_val = vnc_actuelle[0] if len(vnc_actuelle) > 0 else 0
                        st.metric("💼 VNC actuelle", f"{vnc_val:,.2f} €")
                    
                    st.dataframe(df_ecritures, use_container_width=True, hide_index=True)

                    st.divider()
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💾 Sauvegarder", use_container_width=True):
                            rapport = generer_rapport_immobilisation(nom_bien, tableau, mode)
                            sauvegarder_si_autorise(type_analyse="Immobilisation", resultat=rapport)
                            st.success("✅ Sauvegardé !")
                    with col2:
                        rapport = generer_rapport_immobilisation(nom_bien, tableau, mode)
                        try:
                            generer_bouton_word(f"Amortissement_{nom_bien}", rapport)
                        except Exception as e:
                            st.error(f"Erreur : {e}")

    # ── ONGLET 2 : CESSION / SORTIE ──
    with onglet2:
        st.markdown("### 🔄 Calcul de Cession / Sortie d'immobilisation")

        col1, col2 = st.columns(2)
        with col1:
            nom_bien_c = st.text_input("🏷 Désignation", placeholder="Ex: Véhicule X", key="cess_nom")
            valeur_origine_c = st.number_input("💰 Valeur d'origine (€)", min_value=0.0, value=10000.0, key="cess_vo")
            amort_cumule = st.number_input("📉 Amortissements cumulés (€)", min_value=0.0, value=6000.0, key="cess_amort")
        with col2:
            prix_cession = st.number_input("💵 Prix de cession (€)", min_value=0.0, value=5000.0, key="cess_prix")
            date_cession = st.date_input("📅 Date de cession", key="cess_date")
            taux_is = st.number_input("🏛 Taux IS (%)", min_value=0, max_value=100, value=25, key="cess_is")

        if st.button("🔄 Calculer la cession", type="primary", use_container_width=True):
            with st.spinner("Calcul en cours..."):
                result = calculer_cession(valeur_origine_c, amort_cumule, prix_cession, date_cession, taux_is)

                st.markdown(f"## 🔄 Cession — {nom_bien_c}")

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📦 Valeur origine", f"{result['valeur_origine']:,.2f} €")
                with col2:
                    st.metric("📉 VNC", f"{result['vnc']:,.2f} €")
                with col3:
                    delta_color = "normal" if result['resultat_cession'] > 0 else "inverse"
                    st.metric(
                        result['type_resultat'],
                        f"{abs(result['resultat_cession']):,.2f} €",
                        delta=result['type_resultat'],
                        delta_color=delta_color
                    )
                with col4:
                    st.metric("🏛 IS estimé", f"{result['impot_estime']:,.2f} €")

                if result['resultat_cession'] > 0:
                    st.success(f"✅ **Plus-value de cession** : {result['resultat_cession']:,.2f} €")
                else:
                    st.warning(f"⚠ **Moins-value de cession** : {abs(result['resultat_cession']):,.2f} €")

                st.divider()
                st.markdown("### 📚 Écritures Comptables")
                st.dataframe(result['ecritures'], use_container_width=True, hide_index=True)

                st.divider()
                if st.button("💾 Sauvegarder la cession", use_container_width=True):
                    rapport_c = f"Cession {nom_bien_c} : {result['type_resultat']} {result['resultat_cession']:,.2f} €"
                    sauvegarder_si_autorise(type_analyse="Cession Immobilisation", resultat=rapport_c)
                    st.success("✅ Sauvegardé !")

    # ── ONGLET 3 : PLAN D'INVESTISSEMENT ──
    with onglet3:
        st.markdown("### 📊 Plan d'investissement — Suivi du parc")
        st.caption("Uploadez un fichier Excel avec vos immobilisations")

        uploaded_file = st.file_uploader(
            "📎 Fichier immobilisations (CSV, XLSX)",
            type=["csv", "xlsx"],
            help="Colonnes attendues : Désignation, Valeur, Date acquisition, Durée, Amort. cumulé"
        )

        if uploaded_file:
            df, erreur = charger_fichier(uploaded_file)
            if erreur:
                st.error(f"❌ Erreur : {erreur}")
            else:
                st.success(f"✅ {len(df)} immobilisation(s) chargée(s)")
                st.dataframe(df, use_container_width=True, hide_index=True)

                st.divider()
                st.markdown("### 📊 Analyse du parc")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📦 Nombre de biens", len(df))
                with col2:
                    if 'Valeur' in df.columns:
                        st.metric("💰 Valeur totale", f"{pd.to_numeric(df['Valeur'], errors='coerce').sum():,.2f} €")
                with col3:
                    if 'Amort. cumulé' in df.columns:
                        st.metric("📉 Amort. total", f"{pd.to_numeric(df['Amort. cumulé'], errors='coerce').sum():,.2f} €")
        else:
            st.info("💡 Vous pouvez aussi saisir vos immobilisations manuellement via l'onglet Tableau d'amortissement.")
# -----------------------------------------------------------------------------
# INVENTAIRE & CLÔTURE
# -----------------------------------------------------------------------------

elif page == "📋 Inventaire & Clôture":
    st.title("📋 Travaux d'Inventaire & Clôture")
    st.markdown("**Provisions, Régularisations, Stocks, Check-list clôture**")
    st.caption("✨ Opérations de fin d'exercice — Qualité grand cabinet")

    from utils.inventaire import (
        calculer_provision_creances,
        calculer_provision_risque,
        calculer_regularisations,
        calculer_variation_stock,
        generer_checklist_cloture,
        generer_rapport_inventaire
    )

    onglet1, onglet2, onglet3, onglet4 = st.tabs([
        "⚠ Provisions",
        "🔄 Régularisations",
        "📦 Stocks",
        "✅ Check-list Clôture"
    ])

    # ── ONGLET 1 : PROVISIONS ──
    with onglet1:
        st.markdown("### ⚠ Provisions")

        sous_onglet1, sous_onglet2 = st.tabs([
            "Créances douteuses",
            "Risques & Charges"
        ])

        with sous_onglet1:
            st.markdown("#### 📉 Provisions pour créances douteuses")
            st.caption("Compte 491 — Article L123-20 du Code de Commerce")

            col1, col2 = st.columns(2)
            with col1:
                taux_douteux = st.slider("Taux créances douteuses (%)", 0, 100, 50)
            with col2:
                taux_irrecouvrables = st.slider("Taux créances irrécouvrables (%)", 0, 100, 100)

            st.markdown("#### 📋 Saisie des créances clients")

            nb_clients = st.number_input("Nombre de clients à analyser", min_value=1, max_value=20, value=3)

            clients_data = []
            for i in range(int(nb_clients)):
                st.markdown(f"**Client {i+1}**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    nom = st.text_input(f"Nom", key=f"client_nom_{i}", placeholder="SARL X")
                with col2:
                    montant = st.number_input(f"Montant (€)", min_value=0.0, key=f"client_montant_{i}", value=1000.0)
                with col3:
                    anciennete = st.number_input(f"Ancienneté (jours)", min_value=0, key=f"client_anc_{i}", value=90)
                clients_data.append({'Client': nom, 'Montant': montant, 'Ancienneté': anciennete})

            if st.button("⚠ Calculer les provisions", type="primary", use_container_width=True, key="btn_prov_creances"):
                df_clients = pd.DataFrame(clients_data)
                df_resultats, total = calculer_provision_creances(df_clients, taux_douteux, taux_irrecouvrables)

                st.markdown("## 📊 Résultats")
                st.dataframe(df_resultats, use_container_width=True, hide_index=True)

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("💰 Total provisions", f"{total:,.2f} €")
                with col2:
                    nb_douteux = len(df_resultats[df_resultats['Taux (%)'] > 0])
                    st.metric("⚠ Créances à risque", nb_douteux)

                st.divider()
                st.markdown("### 📚 Écriture comptable")
                st.info(f"""
**Dotation aux provisions :**
- Débit **6817** (Dotation provisions créances) : {total:,.2f} €
- Crédit **491** (Provision créances douteuses) : {total:,.2f} €
                """)

                if st.button("💾 Sauvegarder", use_container_width=True, key="save_prov_creances"):
                    sauvegarder_si_autorise(type_analyse="Provisions créances", resultat=df_resultats.to_string())
                    st.success("✅ Sauvegardé !")

        with sous_onglet2:
            st.markdown("#### 🛡 Provisions pour risques et charges")
            st.caption("Compte 15x — Risques identifiés fin d'exercice")

            col1, col2, col3 = st.columns(3)
            with col1:
                libelle_risque = st.text_input("📝 Nature du risque", placeholder="Ex: Litige fournisseur")
            with col2:
                montant_risque = st.number_input("💰 Montant estimé (€)", min_value=0.0, value=5000.0)
            with col3:
                probabilite = st.slider("📊 Probabilité (%)", 0, 100, 70)

            compte_prov = st.selectbox("📚 Compte de provision", [
                "151 — Provisions pour risques",
                "152 — Provisions pour impôts",
                "153 — Provisions pour pensions",
                "155 — Provisions pour garanties",
                "158 — Autres provisions pour charges"
            ])

            if st.button("🛡 Calculer la provision", type="primary", use_container_width=True, key="btn_prov_risque"):
                compte = compte_prov.split(" — ")[0]
                result = calculer_provision_risque(libelle_risque, montant_risque, probabilite, compte)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("💰 Montant risque", f"{montant_risque:,.2f} €")
                with col2:
                    st.metric("📊 Probabilité", f"{probabilite}%")
                with col3:
                    st.metric("⚠ Provision", f"{result['provision']:,.2f} €")

                st.divider()
                st.markdown("### 📚 Écriture comptable")
                st.dataframe(result['ecriture'], use_container_width=True, hide_index=True)

    # ── ONGLET 2 : RÉGULARISATIONS ──
    with onglet2:
        st.markdown("### 🔄 Régularisations de fin d'exercice")
        st.caption("CCA, PCA, Charges à payer, Produits à recevoir")

        with st.expander("ℹ Comprendre les régularisations"):
            st.markdown("""
| Type | Compte | Description |
|---|---|---|
| **CCA** | 486 | Charges payées mais concernant l'exercice suivant |
| **PCA** | 487 | Produits encaissés mais concernant l'exercice suivant |
| **CAP** | 408/428 | Charges dues mais pas encore facturées |
| **PAR** | 418 | Produits à facturer non encore encaissés |
            """)

        date_cloture = st.date_input("📅 Date de clôture de l'exercice")

        nb_elements = st.number_input("Nombre d'éléments à régulariser", min_value=1, max_value=10, value=2)

        elements = []
        for i in range(int(nb_elements)):
            st.markdown(f"**Élément {i+1}**")
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                type_reg = st.selectbox("Type", ["CCA", "PCA", "CAP", "PAR"], key=f"type_{i}")
            with col2:
                lib = st.text_input("Libellé", key=f"lib_{i}", placeholder="Ex: Assurance")
            with col3:
                montant = st.number_input("Montant (€)", min_value=0.0, key=f"mont_{i}", value=1200.0)
            with col4:
                date_debut = st.date_input("Début", key=f"deb_{i}")
            with col5:
                date_fin = st.date_input("Fin", key=f"fin_{i}")

            elements.append({
                'type': type_reg,
                'libelle': lib,
                'montant_total': montant,
                'date_debut': datetime.combine(date_debut, datetime.min.time()),
                'date_fin': datetime.combine(date_fin, datetime.min.time()),
                'date_cloture': datetime.combine(date_cloture, datetime.min.time())
            })

        if st.button("🔄 Calculer les régularisations", type="primary", use_container_width=True):
            df_reg = calculer_regularisations(elements)

            st.markdown("## 📊 Résultats des régularisations")
            st.dataframe(df_reg, use_container_width=True, hide_index=True)

            total_reg = df_reg['Montant régularisé (€)'].sum()
            st.metric("💰 Total à régulariser", f"{total_reg:,.2f} €")

            if st.button("💾 Sauvegarder", use_container_width=True, key="save_reg"):
                sauvegarder_si_autorise(type_analyse="Régularisations", resultat=df_reg.to_string())
                st.success("✅ Sauvegardé !")

    # ── ONGLET 3 : STOCKS ──
    with onglet3:
        st.markdown("### 📦 Ajustement des stocks")
        st.caption("Variation de stock — Écritures comptables automatiques")

        col1, col2, col3 = st.columns(3)
        with col1:
            type_stock = st.selectbox("📦 Type de stock", [
                "marchandises",
                "matieres_premieres",
                "produits_finis",
                "en_cours"
            ])
        with col2:
            stock_debut = st.number_input("📊 Stock début exercice (€)", min_value=0.0, value=50000.0)
        with col3:
            stock_fin = st.number_input("📊 Stock fin exercice (€)", min_value=0.0, value=45000.0)

        if st.button("📦 Calculer la variation", type="primary", use_container_width=True):
            result = calculer_variation_stock(stock_debut, stock_fin, type_stock)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📊 Stock début", f"{stock_debut:,.2f} €")
            with col2:
                st.metric("📊 Stock fin", f"{stock_fin:,.2f} €")
            with col3:
                delta_color = "normal" if result['variation'] > 0 else "inverse"
                st.metric(
                    "🔄 Variation",
                    f"{abs(result['variation']):,.2f} €",
                    delta=result['sens'],
                    delta_color=delta_color
                )

            st.divider()
            st.markdown("### 📚 Écriture comptable")
            st.dataframe(result['ecriture'], use_container_width=True, hide_index=True)

            if st.button("💾 Sauvegarder", use_container_width=True, key="save_stock"):
                sauvegarder_si_autorise(
                    type_analyse="Variation stock",
                    resultat=f"Stock {type_stock} : variation {result['variation']:,.2f} €"
                )
                st.success("✅ Sauvegardé !")

    # ── ONGLET 4 : CHECK-LIST CLÔTURE ──
    with onglet4:
        st.markdown("### ✅ Check-list de clôture d'exercice")
        st.caption("Toutes les opérations à effectuer avant clôture")

        exercice = st.text_input("📅 Exercice", value=str(datetime.now().year))

        if st.button("✅ Générer la check-list", type="primary", use_container_width=True):
            df_checklist = generer_checklist_cloture(exercice)

            # Résumé
            nb_critique = len(df_checklist[df_checklist['Priorité'] == "🔴 Critique"])
            nb_important = len(df_checklist[df_checklist['Priorité'] == "🟡 Important"])

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📋 Total tâches", len(df_checklist))
            with col2:
                st.metric("🔴 Critiques", nb_critique)
            with col3:
                st.metric("🟡 Importantes", nb_important)

            st.divider()

            # Affichage par catégorie
            for categorie in df_checklist['Catégorie'].unique():
                st.markdown(f"#### {categorie}")
                df_cat = df_checklist[df_checklist['Catégorie'] == categorie][['Tâche', 'Priorité', 'Délai']]
                st.dataframe(df_cat, use_container_width=True, hide_index=True)

            st.divider()

            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Sauvegarder", use_container_width=True, key="save_checklist"):
                    sauvegarder_si_autorise(
                        type_analyse="Check-list clôture",
                        resultat=df_checklist.to_string()
                    )
                    st.success("✅ Sauvegardé !")
            with col2:
                try:
                    rapport = f"CHECK-LIST CLÔTURE {exercice}\n\n" + df_checklist.to_string()
                    generer_bouton_word(f"Checklist_Cloture_{exercice}", rapport)
                except Exception as e:
                    st.error(f"Erreur : {e}")

# -----------------------------------------------------------------------------
# 9. RAPPORT CLIENT - VERSION PRO AVEC MODE MANUEL
# -----------------------------------------------------------------------------

elif page == "📋 Rapport Client":
    st.title("📋 Rapport Client")
    st.markdown("**Livrable professionnel** pour vos clients")
    st.caption("✨ Synthèse + KPIs + Analyse + Recommandations")
    
    st.markdown("### 👤 Informations Client")
    
    col1, col2 = st.columns(2)
    with col1:
        nom_client = st.text_input("🏢 Nom du client", placeholder="Ex: SARL DARLING")
        siret = st.text_input("🆔 SIRET")
        secteur = st.text_input("🏭 Secteur d'activité")
    
    with col2:
        periode = st.selectbox("📆 Période", ["Mensuel", "Trimestriel", "Semestriel", "Annuel"])
        exercice = st.number_input("📅 Exercice", min_value=2020, max_value=2030, value=2026)
        date_rapport = st.date_input("📋 Date du rapport")
    
    st.divider()
    
    st.markdown("### 📂 Données Comptables")
    
    uploaded_file = st.file_uploader(
        "📎 Balance ou FEC du client",
        type=["csv", "xlsx", "txt"]
    )
    
    df = None
    if uploaded_file:
        from utils.intelligent_parser import parser_balance_intelligent
        
        mode_lecture = st.radio(
            "🔧 Mode de lecture",
            ["🤖 Auto-détection", "📋 Mode manuel"],
            horizontal=True,
            key="rc_mode"
        )
        
        if mode_lecture == "🤖 Auto-détection":
            try:
                with st.spinner("🤖 Analyse..."):
                    if uploaded_file.name.endswith('xlsx') or uploaded_file.name.endswith('csv'):
                        df, info = parser_balance_intelligent(uploaded_file)
                        st.success(f"✅ {info['format_detecte']} | {len(df):,} comptes")
                        if info['colonnes_manquantes']:
                            st.warning(f"⚠ Colonnes non détectées : {', '.join(info['colonnes_manquantes'])}. Essayez le mode manuel.")
                    else:
                        df = pd.read_csv(uploaded_file, sep='|', encoding='utf-8')
                        st.success(f"✅ FEC chargé : {len(df):,} lignes")
            except Exception as e:
                st.error(f"Erreur : {e}")
        
        else:
            col1, col2 = st.columns(2)
            with col1:
                a_un_entete = st.checkbox("✅ Fichier a une ligne d'en-tête", value=True, key="rc_entete")
            with col2:
                ligne_entete = st.number_input("Ligne d'en-tête", min_value=0, max_value=20, value=0, key="rc_ligne") if a_un_entete else None
            
            try:
                if uploaded_file.name.endswith('xlsx'):
                    df = pd.read_excel(uploaded_file, header=ligne_entete if a_un_entete else None)
                else:
                    df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8', header=ligne_entete if a_un_entete else None)
                
                st.success(f"✅ Fichier chargé : {len(df):,} lignes")
                
                with st.expander("👀 Aperçu"):
                    st.dataframe(df.head(15), use_container_width=True)
                
                st.markdown("#### 🎯 Mapping des colonnes")
                colonnes_disponibles = ["-- Aucune --"] + [str(c) for c in df.columns]
                
                col1, col2 = st.columns(2)
                with col1:
                    col_compte = st.selectbox("🔢 Compte", colonnes_disponibles, index=1 if len(df.columns) > 0 else 0, key="rc_cc")
                    col_debit = st.selectbox("📥 Débit", colonnes_disponibles, index=3 if len(df.columns) > 2 else 0, key="rc_cd")
                with col2:
                    col_libelle = st.selectbox("📝 Libellé", colonnes_disponibles, index=2 if len(df.columns) > 1 else 0, key="rc_cl")
                    col_credit = st.selectbox("📤 Crédit", colonnes_disponibles, index=4 if len(df.columns) > 3 else 0, key="rc_cre")
                
                renommage = {}
                if col_compte != "-- Aucune --":
                    renommage[col_compte] = 'CompteNum'
                if col_libelle != "-- Aucune --":
                    renommage[col_libelle] = 'CompteLib'
                if col_debit != "-- Aucune --":
                    renommage[col_debit] = 'Debit'
                if col_credit != "-- Aucune --":
                    renommage[col_credit] = 'Credit'
                
                df = df.rename(columns=renommage)
                
            except Exception as e:
                st.error(f"Erreur : {e}")
    
    st.divider()
    
    st.markdown("### ✍ Personnalisation")
    
    col1, col2 = st.columns(2)
    with col1:
        observations = st.text_area(
            "📝 Observations particulières",
            placeholder="Évènements marquants, points d'attention...",
            height=120
        )
    with col2:
        objectifs = st.text_area(
            "🎯 Objectifs prochaine période",
            placeholder="Objectifs de croissance, plans d'action...",
            height=120
        )
    
    st.divider()
    
    if st.button("📋 Générer le Rapport Client", type="primary", use_container_width=True):
        if not nom_client:
            st.error("⚠ Veuillez renseigner le nom du client")
        else:
            from utils.rapport_client import generer_rapport_client, analyser_donnees_client
            
            df_analyse = df if df is not None else pd.DataFrame()
            
            with st.spinner("Génération du rapport..."):
                rapport = generer_rapport_client(
                    nom_client=nom_client,
                    siret=siret,
                    periode=periode,
                    exercice=exercice,
                    donnees=df_analyse,
                    observations=observations,
                    objectifs=objectifs
                )
                
                if df is not None and 'CompteNum' in df.columns:
                    kpis = analyser_donnees_client(df)
                    
                    if kpis.get('chiffre_affaires', 0) > 0:
                        st.markdown("## 📊 Aperçu KPIs Client")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("CA", f"{kpis['chiffre_affaires']:,.0f} €")
                        with col2:
                            rn = kpis['resultat_net']
                            st.metric("Résultat Net", f"{rn:,.0f} €",
                                     delta="Bénéfice" if rn > 0 else "Déficit",
                                     delta_color="normal" if rn > 0 else "inverse")
                        with col3:
                            st.metric("EBE", f"{kpis['ebe']:,.0f} €")
                        with col4:
                            st.metric("Trésorerie", f"{kpis['tresorerie']:,.0f} €")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Marge nette", f"{kpis['taux_rentabilite']:.1f}%")
                        with col2:
                            st.metric("Marge brute", f"{kpis['taux_marge_brute']:.1f}%")
                        with col3:
                            st.metric("Taux VA", f"{kpis['taux_va']:.1f}%")
                        with col4:
                            st.metric("Poids personnel", f"{kpis['poids_charges_personnel']:.1f}%")
                        
                        st.divider()
                
                st.markdown("## 📄 Rapport Généré")
                with st.container():
                    afficher_rapport(rapport, afficher_kpis_auto=True, afficher_alertes_auto=True, afficher_tables_auto=True, compact=True)
                
                st.divider()
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Sauvegarder", use_container_width=True):
                        sauvegarder_si_autorise(type_analyse="Rapport Client", resultat=rapport)
                        st.success("✅ Sauvegardé !")
                
                with col2:
                    try:
                        nom_fichier = f"Rapport_{nom_client.replace(' ', '_')}_{periode}_{exercice}"
                        generer_bouton_word(nom_fichier, rapport)
                    except Exception as e:
                        st.error(f"Erreur : {e}")

# -----------------------------------------------------------------------------
# 10. ALERTES & ANOMALIES - VERSION PROFESSIONNELLE
# -----------------------------------------------------------------------------

elif page == "⚠ Alertes & Anomalies":
    st.title("⚠ Alertes & Anomalies")
    st.markdown("**Détection automatique** d'anomalies multi-niveaux")
    st.caption("✨ 10 contrôles automatiques pour cabinets et DAF")
    
    with st.expander("ℹ Quels contrôles sont effectués ?"):
        st.markdown("""
        Le module détecte automatiquement :
        
        🔴 **CRITIQUE**
        - Déséquilibre Débit/Crédit
        
        🟡 **WARNING**
        - Doublons exacts
        - Montants ronds suspects (>30%)
        - Écritures sans libellé
        - Montants négatifs
        - Débit ET Crédit simultanés
        - Numéros de comptes invalides
        
        🔵 **INFO**
        - Écritures montant nul
        - Montants très répétés
        - Écritures week-end
        - Montants très élevés (>10x P95)
        - Charges créditrices
        """)
    
    uploaded_file = st.file_uploader(
        "📎 Données comptables (FEC, Balance, CSV, XLSX)",
        type=["csv", "xlsx", "txt"]
    )
    
    if uploaded_file:
        from utils.alertes import detecter_alertes, generer_rapport_alertes
        from utils.intelligent_parser import parser_balance_intelligent
        
        try:
            with st.spinner("🤖 Analyse..."):
                if uploaded_file.name.endswith('xlsx') or uploaded_file.name.endswith('csv'):
                    try:
                        df, info = parser_balance_intelligent(uploaded_file)
                        st.success(f"✅ Format détecté : **{info['format_detecte']}** | **{len(df):,} lignes**")
                    except:
                        if uploaded_file.name.endswith('xlsx'):
                            df = pd.read_excel(uploaded_file)
                        else:
                            df = pd.read_csv(uploaded_file, sep=None, engine='python')
                        st.success(f"✅ Fichier chargé : **{len(df):,} lignes**")
                else:
                    df = pd.read_csv(uploaded_file, sep='|', encoding='utf-8')
                    st.success(f"✅ FEC chargé : **{len(df):,} lignes**")
            
            with st.expander("👀 Aperçu"):
                st.dataframe(df.head(10), use_container_width=True)
            
            st.divider()
            
            nom_entreprise = st.text_input("🏢 Nom de l'entreprise", value="Entreprise")
            
            if st.button("🔍 Détecter les anomalies", type="primary", use_container_width=True):
                with st.spinner("Analyse en cours..."):
                    alertes = detecter_alertes(df)
                    
                    nb_critique = len([a for a in alertes if a['niveau'] == 'CRITIQUE'])
                    nb_warning = len([a for a in alertes if a['niveau'] == 'WARNING'])
                    nb_info = len([a for a in alertes if a['niveau'] == 'INFO'])
                    
                    st.markdown("## 📊 Résumé des Alertes")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("🔴 Critiques", nb_critique,
                                 delta_color="inverse" if nb_critique > 0 else "normal")
                    with col2:
                        st.metric("🟡 Warnings", nb_warning)
                    with col3:
                        st.metric("🔵 Infos", nb_info)
                    with col4:
                        st.metric("📊 Total", len(alertes))
                    
                    if nb_critique > 0:
                        st.error("🚨 **ATTENTION** : Anomalies critiques détectées - Investigation urgente !")
                    elif nb_warning > 0:
                        st.warning("⚠ **Vigilance** : Alertes à investiguer")
                    elif len(alertes) == 0:
                        st.success("✅ **Aucune anomalie majeure détectée** - Données saines")
                    else:
                        st.info("ℹ **Points à surveiller** identifiés")
                    
                    st.divider()
                    
                    if alertes:
                        alertes_critiques = [a for a in alertes if a['niveau'] == 'CRITIQUE']
                        if alertes_critiques:
                            st.markdown("### 🔴 Alertes CRITIQUES")
                            for a in alertes_critiques:
                                st.error(f"**{a['titre']}** ({a['count']}) : {a['message']}")
                        
                        alertes_warning = [a for a in alertes if a['niveau'] == 'WARNING']
                        if alertes_warning:
                            st.markdown("### 🟡 Alertes WARNING")
                            for a in alertes_warning:
                                st.warning(f"**{a['titre']}** ({a['count']}) : {a['message']}")
                        
                        alertes_info = [a for a in alertes if a['niveau'] == 'INFO']
                        if alertes_info:
                            st.markdown("### 🔵 Alertes INFO")
                            for a in alertes_info:
                                st.info(f"**{a['titre']}** ({a['count']}) : {a['message']}")
                    
                    st.divider()
                    
                    rapport = generer_rapport_alertes(alertes, nom_entreprise)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💾 Sauvegarder", use_container_width=True):
                            sauvegarder_si_autorise(type_analyse="Alertes", resultat=rapport)
                            st.success("✅ Sauvegardé !")
                    with col2:
                        try:
                            generer_bouton_word(f"Alertes_{nom_entreprise}", rapport)
                        except Exception as e:
                            st.error(f"Erreur : {e}")
                            
        except Exception as e:
            st.error(f"❌ Erreur : {str(e)}")
            import traceback
            with st.expander("Détails techniques"):
                st.code(traceback.format_exc())

# -----------------------------------------------------------------------------
# 11. COHÉRENCE DES DONNÉES - VERSION PROFESSIONNELLE
# -----------------------------------------------------------------------------

elif page == "✅ Cohérence des Données":
    st.title("✅ Cohérence des Données")
    st.markdown("**Audit qualité** des données comptables")
    st.caption("✨ 7 contrôles automatiques + Score qualité")
    
    with st.expander("ℹ Quels contrôles ?"):
        st.markdown("""
        1. **Complétude des données** (20 pts)
        2. **Unicité / Doublons** (15 pts)
        3. **Équilibre Débit/Crédit** (25 pts)
        4. **Format des comptes** (15 pts)
        5. **Format des dates** (15 pts)
        6. **Libellés renseignés** (10 pts)
        
        **Total : 100 points**
        """)
    
    uploaded_file = st.file_uploader(
        "📎 Données comptables",
        type=["csv", "xlsx", "txt"]
    )
    
    if uploaded_file:
        from utils.coherence import verifier_coherence
        from utils.intelligent_parser import parser_balance_intelligent
        
        try:
            with st.spinner("🤖 Analyse..."):
                if uploaded_file.name.endswith('xlsx') or uploaded_file.name.endswith('csv'):
                    try:
                        df, info = parser_balance_intelligent(uploaded_file)
                        st.success(f"✅ Format : **{info['format_detecte']}** | **{len(df):,} lignes**")
                    except:
                        if uploaded_file.name.endswith('xlsx'):
                            df = pd.read_excel(uploaded_file)
                        else:
                            df = pd.read_csv(uploaded_file, sep=None, engine='python')
                        st.success(f"✅ Fichier chargé : **{len(df):,} lignes**")
                else:
                    df = pd.read_csv(uploaded_file, sep='|', encoding='utf-8')
                    st.success(f"✅ FEC : **{len(df):,} lignes**")
            
            with st.expander("👀 Aperçu"):
                st.dataframe(df.head(10), use_container_width=True)
            
            st.divider()
            
            nom_entreprise = st.text_input("🏢 Nom de l'entreprise", value="Entreprise")
            
            if st.button("🔍 Vérifier la cohérence", type="primary", use_container_width=True):
                with st.spinner("Vérifications en cours..."):
                    resultat = verifier_coherence(df)
                    
                    st.markdown("## 🎯 Score de Qualité")
                    
                    score = resultat['score_qualite']
                    niveau = resultat.get('niveau', 'N/A')
                    
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if score >= 90:
                            st.success(f"### {niveau} : {score}% ✅")
                        elif score >= 75:
                            st.info(f"### {niveau} : {score}% ℹ")
                        elif score >= 50:
                            st.warning(f"### {niveau} : {score}% ⚠")
                        else:
                            st.error(f"### {niveau} : {score}% ❌")
                        
                        st.progress(int(score))
                    
                    st.divider()
                    
                    kpis = resultat.get('kpis', {})
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("📝 Lignes", f"{kpis.get('nb_lignes', 0):,}")
                    with col2:
                        st.metric("📊 Colonnes", kpis.get('nb_colonnes', 0))
                    with col3:
                        st.metric("✅ Complétude", f"{kpis.get('completude', 0):.1f}%")
                    with col4:
                        st.metric("⚠ Doublons", kpis.get('doublons', 0),
                                 delta_color="inverse" if kpis.get('doublons', 0) > 0 else "normal")
                    
                    st.divider()
                    
                    st.markdown("## 🔍 Vérifications Effectuées")
                    
                    for nom, ctrl in resultat['verifications'].items():
                        if ctrl['status'] == 'OK':
                            st.success(f"✅ **{nom}** : {ctrl['message']}")
                        elif ctrl['status'] == 'WARNING':
                            st.warning(f"⚠ **{nom}** : {ctrl['message']}")
                        else:
                            st.error(f"❌ **{nom}** : {ctrl['message']}")
                    
                    st.divider()
                    
                    if resultat['recommandations']:
                        st.markdown("## 💡 Recommandations")
                        for reco in resultat['recommandations']:
                            st.info(f"💼 {reco}")
                    
                    st.divider()
                    
                    rapport = generer_rapport_coherence(resultat, nom_entreprise)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💾 Sauvegarder", use_container_width=True):
                            sauvegarder_si_autorise(type_analyse="Cohérence", resultat=rapport)
                            st.success("✅ Sauvegardé !")
                    with col2:
                        try:
                            generer_bouton_word(f"Coherence_{nom_entreprise}", rapport)
                        except Exception as e:
                            st.error(f"Erreur : {e}")
                            
        except Exception as e:
            st.error(f"❌ Erreur : {str(e)}")

# -----------------------------------------------------------------------------
# 12. VEILLE FISCALE
# -----------------------------------------------------------------------------

elif page == "📰 Veille Fiscale":
    st.title("📰 Veille Fiscale")
    st.markdown("**Actualités fiscales officielles** — France")
    st.caption("✨ Sources : DGFiP, BOFiP, Légifrance")

    onglet1, onglet2 = st.tabs([
        "🇫🇷 Fiscalité France",
        "❓ Question Fiscale IA"
    ])

    with onglet1:
        st.markdown("### 📡 Sources Officielles Françaises")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.info("**DGFiP**\nDirection Générale des Finances Publiques")
            st.markdown("[🔗 impots.gouv.fr](https://www.impots.gouv.fr)")
        with col2:
            st.info("**BOFiP**\nBulletin Officiel des Finances Publiques")
            st.markdown("[🔗 bofip.impots.gouv.fr](https://bofip.impots.gouv.fr)")
        with col3:
            st.info("**Légifrance**\nTextes législatifs et réglementaires")
            st.markdown("[🔗 legifrance.gouv.fr](https://www.legifrance.gouv.fr)")

        st.divider()

        if st.button("🔄 Actualiser la veille France", type="primary", use_container_width=True):
            with st.spinner("Récupération des actualités fiscales françaises..."):
                try:
                    actualites = obtenir_veille_fiscale()

                    if actualites and len(actualites) > 0:
                        st.success(f"✅ {len(actualites)} actualité(s) récupérée(s)")

                        for idx, article in enumerate(actualites):
                            if isinstance(article, dict):
                                titre = article.get('titre', 'Sans titre')
                                date = article.get('date', 'Date inconnue')
                                resume = article.get('resume', '')
                                lien = article.get('lien', '')
                                source = article.get('source', 'Source officielle')

                                with st.expander(f"📄 {titre}"):
                                    col1, col2 = st.columns([2, 1])
                                    with col1:
                                        st.caption(f"🗓 {date} | 📡 {source}")
                                    with col2:
                                        if lien:
                                            st.markdown(f"[🔗 Article complet]({lien})")
                                    if resume:
                                        st.markdown(resume)

                                    if st.button(f"🤖 Analyser avec IA", key=f"ia_{idx}"):
                                        with st.spinner("Analyse IA..."):
                                            prompt = f"""En tant qu'expert fiscal français, analyse cette actualité :

Titre : {titre}
Résumé : {resume}

Fournis :
1. Impact pour les TPE/PME françaises
2. Actions à entreprendre
3. Délais à respecter
4. Références légales (CGI, BOFiP)"""
                                            result = appel_mistral_securise(prompt, temperature=0.2, label="analyse fiscale")
                                            if result["success"]:
                                                st.markdown("#### 💡 Analyse Cabinet")
                                                st.markdown(result["content"])

                        sauvegarder_si_autorise(type_analyse="Veille Fiscale France", resultat=str(actualites))

                    else:
                        st.info("ℹ Aucune actualité récente. Consultez directement les sources officielles.")

                except Exception as e:
                    st.error(f"❌ Erreur de récupération : {str(e)}")

        st.divider()

        annee = datetime.now().year
        st.markdown(f"### 📅 Calendrier Fiscal France {annee}")

        echeances = [
            {"Échéance": f"15 janvier", "Obligation": "TVA mensuelle — décembre N-1", "Concerne": "Régime réel normal"},
            {"Échéance": f"31 janvier", "Obligation": "DSN mensuelle", "Concerne": "Employeurs"},
            {"Échéance": f"15 février", "Obligation": "TVA mensuelle — janvier", "Concerne": "Régime réel normal"},
            {"Échéance": f"31 mars", "Obligation": f"Liasse fiscale IS — clôture 31/12/{annee-1}", "Concerne": "Sociétés IS"},
            {"Échéance": f"30 avril", "Obligation": f"Déclaration revenus {annee-1}", "Concerne": "Particuliers"},
            {"Échéance": f"15 juin", "Obligation": "Acompte IS — 1er versement", "Concerne": "Sociétés IS"},
            {"Échéance": f"30 juin", "Obligation": f"Liasse fiscale IS — clôture 31/03/{annee}", "Concerne": "Sociétés IS"},
            {"Échéance": f"15 septembre", "Obligation": "Acompte IS — 2ème versement", "Concerne": "Sociétés IS"},
            {"Échéance": f"15 décembre", "Obligation": "Acompte IS — 4ème versement", "Concerne": "Sociétés IS"},
        ]

        _MOIS_FR = {
            "janvier": 1, "février": 2, "mars": 3, "avril": 4,
            "mai": 5, "juin": 6, "juillet": 7, "août": 8,
            "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12
        }

        def _parse_echeance(date_str, annee):
            """Parse une date FR sans dépendance locale."""
            parts = date_str.strip().split()
            if len(parts) == 2:
                jour, mois_str = parts
                mois_num = _MOIS_FR.get(mois_str.lower())
                if mois_num:
                    return datetime(int(annee), mois_num, int(jour))
            return None

        aujourd_hui = datetime.now()
        echeances_enrichies = []
        for e in echeances:
            date_echeance = _parse_echeance(e["Échéance"], annee)
            if date_echeance:
                jours_restants = (date_echeance - aujourd_hui).days
                if 0 <= jours_restants <= 30:
                    e["Statut"] = f"⚠ Dans {jours_restants} jours"
                elif jours_restants < 0:
                    e["Statut"] = "✅ Passée"
                else:
                    e["Statut"] = f"📅 Dans {jours_restants} jours"
            else:
                e["Statut"] = "📅"
            echeances_enrichies.append(e)

        df_echeances = pd.DataFrame(echeances_enrichies)
        st.dataframe(df_echeances, use_container_width=True, hide_index=True)

    with onglet2:
        st.markdown("### 🤖 Posez votre question fiscale à l'IA")
        st.caption("Fiscalité française — CGI, BOFiP, LPF")

        question = st.text_area(
            "📝 Votre question",
            placeholder="Ex: Quel est le taux de TVA applicable aux prestations de services ?",
            height=120
        )

        if st.button("🤖 Obtenir une réponse IA", type="primary", use_container_width=True) and question:
            with st.spinner("Analyse fiscale en cours..."):
                prompt = f"""En tant qu'expert en fiscalité française (CGI, BOFiP, LPF), réponds à cette question professionnelle :

{question}

Structure ta réponse ainsi :
1. **Réponse directe et précise**
2. **Références légales** (articles CGI, BOFiP)
3. **Exemple chiffré** si pertinent
4. **Points d'attention** et risques à éviter
5. **Recommandation cabinet**"""

                result = appel_mistral_securise(prompt, temperature=0.2, label="question fiscale")

                if result["success"]:
                    st.markdown("### 💡 Réponse Expert")
                    st.markdown(result["content"])

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💾 Sauvegarder", use_container_width=True):
                            sauvegarder_si_autorise(
                                type_analyse="Question Fiscale IA",
                                resultat=result["content"]
                            )
                            st.success("✅ Sauvegardé !")
                    with col2:
                        try:
                            generer_bouton_word("Reponse_Fiscale", result["content"])
                        except Exception as e:
                            st.error(f"Erreur : {e}")

                    st.caption("⚠ Réponse à titre informatif. Consultez un expert pour validation.")


# -----------------------------------------------------------------------------
# 13. TARIFS & ABONNEMENT
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
    st.markdown("**Engagements SMD Consulting** envers la protection de vos données")
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.success("### ✅ Anonymisation\n\nVous transmettez uniquement des données anonymisées : SIRET masqués, noms supprimés, données sensibles retirées.")
    with col2:
        st.success("### ✅ Non stockées\n\nVos données ne sont pas conservées après analyse. Une convention de test est disponible sur demande.")
    with col3:
        st.success("### ✅ IA éthique\n\nVos données ne servent pas à entraîner Mistral AI — garanti contractuellement.")

    st.divider()
    st.markdown("### 📋 Convention de Test")
    st.info("""
**CONVENTION DE TEST - SMD Consulting**

Entre **SMD Consulting** (Souleymane Diallo) et le client soussigné, il est convenu que :

1. Les données transmises sont utilisées **uniquement** pour la démonstration du Superviseur IA Comptable
2. **Aucune donnée n'est conservée** au-delà de la session d'analyse
3. Les données ne sont **pas partagées** avec des tiers
4. Les données ne sont **pas utilisées** pour entraîner des modèles d'IA
5. Le client s'engage à transmettre des données **préalablement anonymisées**

*Version signée disponible sur demande : smdconsulting@gmail.com*
    """)

    st.divider()
    st.markdown("### 🛡 Cadre Réglementaire")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
**RGPD**
- Traitement limité à la finalité déclarée
- Durée de conservation minimale
- Droit d'accès et suppression garanti
- Pas de transfert hors UE sans garanties
        """)
    with col2:
        st.markdown("""
**Mistral AI**
- Données API non utilisées pour l'entraînement
- Traitement en Europe
- Confidentialité contractuellement garantie
        """)

# =============================================================================
# FOOTER
# =============================================================================
st.divider()
st.caption("SMD Consulting © 2026 - Superviseur IA Comptable - contact@smdconsulting.pro")
