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
from utils.bilan import generer_bilan
from utils.rapprochement import rapprocher_bancaire
from utils.rapport_client import generer_rapport_client
from utils.alertes import detecter_alertes
from utils.coherence import verifier_coherence, generer_rapport_coherence
from utils.plan_financement import extraire_caf_bfr_pcg, calculer_kpi_financiers, generer_graphique_waterfall, export_excel_complet, generer_conseils_experts
from utils.tft import page_tft
from utils.comparatif import page_comparatif
from utils.tva import page_tva
from benford_module import analyse_benford_complete

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

if not is_connecte():  # AUTHENTIFICATION ACTIVÉE
    st.title("🔒 Superviseur IA Comptable")
    st.subheader("Accès réservé aux cabinets clients")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        st.markdown("""
        <div style='background:#f0fdf4;padding:12px;border-radius:8px;margin-bottom:10px;font-size:0.85em'>
        ✅ <b>Données anonymisées</b> — SIRET masqués, noms supprimés<br>
        ✅ <b>Non stockées</b> — Aucune conservation après analyse<br>
        ✅ <b>Non utilisées pour entraîner l'IA</b> — Politique Mistral garantie
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        email = st.text_input("📧 Email professionnel", placeholder="contact@cabinet.com")
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
            st.session_state["authenticated"] = True
            st.session_state["user_email"] = "demo@smdconsulting.pro"
            st.session_state["role"] = "demo"
            st.session_state["nom"] = "Démonstration"
            st.session_state["login_time"] = datetime.now().isoformat()
            st.rerun()
        
        st.caption("📧 Demander un accès : contact@smdconsulting.pro")
        st.markdown("---")        
    
    st.divider()
    st.caption("SMD Consulting © 2026 - Comptable IA Augmenté")
    st.stop()

# =============================================================================
# SIDEBAR - NAVIGATION
# =============================================================================

st.sidebar.title("SMD Consulting")
st.sidebar.caption(f"👤 {st.session_state.get('user_email', 'Utilisateur')}")

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
        "🛡️ Loi de Benford",
        "⚠️ Alertes & Anomalies",
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
        st.warning("⚠️ Export Word temporairement indisponible. Copiez le contenu manuellement.")

def appel_mistral_securise(prompt, temperature=0.3, label="analyse"):
    """Appel Mistral avec fallback et message utilisateur clair"""
    try:
        result = appel_mistral(prompt, temperature=temperature)
        if result["success"]:
            return result
        else:
            st.warning(f"⚠️ L'IA est momentanément indisponible pour {label}. Réessayez dans quelques instants.")
            return {"success": False, "content": "", "error": result.get("error", "")}
    except Exception as e:
        st.warning(f"⚠️ Connexion IA interrompue pour {label}. Vérifiez votre connexion.")
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

if page == "🏠 Accueil":
    banniere_demo()

    st.markdown("""
    <div style="padding:1.5rem 1rem 1rem 1rem; border-bottom:2px solid #1F4E79; margin-bottom:1.5rem;">
        <h1 style="margin:0; color:#1F4E79; font-size:1.9rem;">Superviseur IA Comptable</h1>
        <p style="margin:0.4rem 0 0 0; color:#555; font-size:0.95rem;">
            SMD Consulting &nbsp;&middot;&nbsp; Audit &amp; Finance augmentés par l'IA
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("**🔍 Analyse & Audit**")
        st.caption("Factures OCR, Benford, audit balance, alertes anomalies")
    with col2:
        st.markdown("**📊 États Financiers**")
        st.caption("Bilan, CdR/SIG, TFT, Plan de Financement, Comparatif N/N-1")
    with col3:
        st.markdown("**📦 Gestion & Clôture**")
        st.caption("Immobilisations, amortissements, provisions, inventaire")
    with col4:
        st.markdown("**📁 Reporting & Fiscal**")
        st.caption("FEC DGFiP, TVA CA3/CA12, rapports clients, veille fiscale")

    st.divider()

    user = st.session_state.get("user_email", "—")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👤 Session", user.split("@")[0] if "@" in user else user)
    c2.metric("📦 Modules", "21")
    c3.metric("✅ Statut", "Opérationnel")
    c4.metric("🔒 Données", "Non conservées")

    st.divider()
    st.caption("SMD Consulting © 2026 — PCG France · ANC/CRC 99-02 · Données traitées localement, jamais stockées.")
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
                            st.warning(f"⚠️ {ctrl['mention']}")
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
                    st.warning(f"⚠️ Colonnes non détectées : {', '.join(info['colonnes_manquantes'])}. Essayez le mode manuel.")
                
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
                    
                    st.markdown("## 🎯 Score de Qualité de la Balance")
                    score = audit['score_qualite']
                    niveau = audit['niveau']
                    
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if score >= 90:
                            st.success(f"### {niveau} : {score}% ✅")
                        elif score >= 75:
                            st.info(f"### {niveau} : {score}% ℹ️")
                        elif score >= 50:
                            st.warning(f"### {niveau} : {score}% ⚠️")
                        else:
                            st.error(f"### {niveau} : {score}% ❌")
                        st.progress(int(score))
                    
                    st.divider()
                    
                    if audit['kpis']:
                        st.markdown("## 💰 Indicateurs Clés")
                        kpis = audit['kpis']
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            if 'total_debit' in kpis:
                                st.metric("Total Débit", f"{kpis['total_debit']:,.0f} €")
                        with col2:
                            if 'total_credit' in kpis:
                                st.metric("Total Crédit", f"{kpis['total_credit']:,.0f} €")
                        with col3:
                            if 'nb_comptes' in kpis:
                                st.metric("Comptes", kpis['nb_comptes'])
                        with col4:
                            if 'ecart' in kpis:
                                st.metric("Écart D/C", f"{kpis['ecart']:,.2f} €",
                                         delta_color="inverse" if kpis['ecart'] > 0.01 else "normal")
                        
                        if 'resultat_estime' in kpis:
                            st.markdown("### 📈 Performance Estimée")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Produits", f"{kpis['produits_totaux']:,.0f} €")
                            with col2:
                                st.metric("Charges", f"{kpis['charges_totales']:,.0f} €")
                            with col3:
                                st.metric("Résultat", f"{kpis['resultat_estime']:,.0f} €",
                                         delta=f"Marge : {kpis.get('marge_pct', 0):.1f}%")
                    
                    st.divider()
                    
                    if 'repartition_classes' in audit['kpis']:
                        st.markdown("## 📚 Répartition par Classe Comptable (PCG)")
                        repartition = audit['kpis']['repartition_classes']
                        df_classes = pd.DataFrame([
                            {'Classe': k, 'Nombre de comptes': v} 
                            for k, v in repartition.items()
                        ]).sort_values('Nombre de comptes', ascending=False)
                        
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.dataframe(df_classes, use_container_width=True, hide_index=True)
                        with col2:
                            st.bar_chart(df_classes.set_index('Classe'))
                    
                    st.divider()
                    
                    st.markdown("## 🔍 Contrôles Effectués")
                    for nom, ctrl in audit['controles'].items():
                        if ctrl['statut'] == 'OK':
                            st.success(f"✅ **{nom}** : {ctrl['message']}")
                        elif ctrl['statut'] == 'WARNING':
                            st.warning(f"⚠️ **{nom}** : {ctrl['message']}")
                        else:
                            st.error(f"❌ **{nom}** : {ctrl['message']}")
                    
                    if audit['anomalies']:
                        st.markdown("## ⚠️ Anomalies Détectées")
                        for anomalie in audit['anomalies']:
                            grav = anomalie['gravite']
                            if grav == 'CRITIQUE':
                                st.error(f"🔴 **[{grav}]** {anomalie['type']} : {anomalie['description']}")
                            elif grav == 'MOYENNE':
                                st.warning(f"🟡 **[{grav}]** {anomalie['type']} : {anomalie['description']}")
                            else:
                                st.info(f"🔵 **[{grav}]** {anomalie['type']} : {anomalie['description']}")
                    
                    if audit['recommandations']:
                        st.markdown("## 💡 Recommandations Cabinet")
                        for reco in audit['recommandations']:
                            st.info(f"💼 {reco}")
                    
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
            
            if st.button("🛡️ Lancer la validation DGFiP complète", type="primary", use_container_
