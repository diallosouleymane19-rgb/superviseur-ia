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
from utils.compte_resultat import generer_compte_resultat
from utils.rapprochement import rapprocher_bancaire
from utils.rapport_client import generer_rapport_client
from utils.alertes import detecter_alertes
from utils.coherence import verifier_coherence
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

if False:  # AUTHENTIFICATION DÉSACTIVÉE TEMPORAIREMENT
    st.title("🔒 Superviseur IA Comptable")
    st.subheader("Accès réservé aux cabinets clients")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
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
        st.info("💡 **Identifiants de test** :\n- Email : `smdconsulting@gmail.com`\n- Mot de passe : `SMDConsulting2026!`")
    
    st.divider()
    st.caption("SMD Consulting © 2026 - Comptable IA Augmenté")
    st.stop()

# =============================================================================
# SIDEBAR - NAVIGATION
# =============================================================================

st.sidebar.title("SMD Consulting")
st.sidebar.caption(f"👤 {st.session_state.get('user_email', 'Utilisateur')}")
st.sidebar.divider()

st.sidebar.subheader("Modules de supervision")

# Menu de navigation avec TOUS les modules
page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Accueil",
        "🧾 Analyse Facture (OCR)",
        "📊 Audit Balance",
        "📂 Traitement FEC",
        "🛡️ Loi de Benford",
        "📈 Compte de Résultat",
        "📊 Bilan Comptable",
        "🔄 Rapprochement Bancaire",
        "📋 Rapport Client",
        "⚠️ Alertes & Anomalies",
        "✅ Cohérence des Données",
        "📰 Veille Fiscale"
    ]
)

st.sidebar.divider()

if st.sidebar.button("🚪 Déconnexion", use_container_width=True):
    logout()

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

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
        st.error(f"Erreur lors de la génération du fichier Word : {e}")


def afficher_stats_rapides(df):
    """Affiche des statistiques rapides sur un DataFrame"""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total lignes", f"{len(df):,}")
    with col2:
        st.metric("Colonnes", len(df.columns))
    with col3:
        if 'Montant' in df.columns or 'Debit' in df.columns:
            montant_col = 'Montant' if 'Montant' in df.columns else 'Debit'
            total = df[montant_col].sum()
            st.metric("Total montants", f"{total:,.2f} €")
    with col4:
        st.metric("Complet à", f"{100 - (df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100):.1f}%")


# =============================================================================
# PAGES / MODULES
# =============================================================================

# -----------------------------------------------------------------------------
# 1. ACCUEIL
# -----------------------------------------------------------------------------

if page == "🏠 Accueil":
    st.title("🏠 Superviseur IA Comptable")
    st.subheader("Plateforme d'audit et de supervision comptable augmentée par Intelligence Artificielle")
    
    st.markdown("""
    ### 🎯 Bienvenue dans votre outil de comptabilité augmentée
    
    Le **Superviseur IA Comptable** de SMD Consulting vous permet de :
    
    #### 📊 Analyse & Audit
    - **Analyse automatique de factures** via OCR (PDF, images)
    - **Détection de fraude** avec la Loi de Benford
    - **Vérification de cohérence** des écritures comptables
    - **Audit de balance** automatisé
    
    #### 📈 États Financiers
    - **Compte de résultat** automatique
    - **Bilan comptable** généré depuis FEC
    - **Rapprochements bancaires** intelligents
    
    #### 🔍 Supervision
    - **Traitement FEC** conforme DGFiP
    - **Alertes intelligentes** sur anomalies
    - **Rapports clients** personnalisés
    - **Veille fiscale** automatique
    
    ### 🚀 Commencer
    
    Sélectionnez un module dans le menu latéral pour démarrer votre analyse.
    """)
    
    st.divider()
    
    # Statistiques d'utilisation
    st.subheader("📊 Votre Session")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Connecté en tant que", st.session_state.get('user_email', 'Utilisateur'))
    with col2:
        st.metric("Modules disponibles", "12")
    with col3:
        st.metric("Statut", "✅ Opérationnel")
    
    st.divider()
    st.caption("**SMD Consulting** - Comptable IA Augmenté © 2026")


# -----------------------------------------------------------------------------
# 2. ANALYSE FACTURE (OCR) - VERSION AMÉLIORÉE
# -----------------------------------------------------------------------------

elif page == "🧾 Analyse Facture (OCR)":
    st.title("🧾 Analyse de Facture")
    st.markdown("**Extraction automatique** des données de factures via OCR + IA")
    
    # Initialisation de l'état
    if 'ocr_resultat' not in st.session_state:
        st.session_state.ocr_resultat = None
    if 'ocr_analyse_ia' not in st.session_state:
        st.session_state.ocr_analyse_ia = None
    
    # Upload + Bouton Reset
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
        if st.button("🔄", help="Nouvelle analyse"):
            st.session_state.ocr_resultat = None
            st.session_state.ocr_analyse_ia = None
            st.rerun()
    
    if uploaded_file:
        # Étape 1 : OCR
        if st.session_state.ocr_resultat is None:
            with st.spinner("🔍 Extraction du texte en cours..."):
                try:
                    texte_extrait = ocr_image_mistral(uploaded_file)
                    
                    if texte_extrait:
                        st.session_state.ocr_resultat = texte_extrait
                        st.rerun()
                    else:
                        st.error("❌ Impossible d'extraire le texte de la facture")
                        
                except Exception as e:
                    st.error(f"❌ Erreur : {str(e)}")
        
        # Affichage du résultat OCR
        if st.session_state.ocr_resultat:
            st.success("✅ Texte extrait avec succès !")
            
            # Texte brut dans un expander
            with st.expander("📄 Voir le texte extrait (brut)", expanded=False):
                st.code(st.session_state.ocr_resultat, language="text")
            
            st.divider()
            
            # Étape 2 : Analyse IA
            if st.session_state.ocr_analyse_ia is None:
                if st.button("🤖 Analyser avec IA", type="primary", use_container_width=True):
                    with st.spinner("🤖 Analyse intelligente en cours..."):
                        prompt = f"""Analyse cette facture de manière structurée :

{st.session_state.ocr_resultat}

Fournis une analyse détaillée avec :
1. Informations générales (fournisseur, client, n° facture, date)
2. Détails des prestations (description, quantités, prix)
3. Calculs (HT, TVA, TTC)
4. Vérifications et conformité
5. Observations éventuelles"""
                        
                        result = appel_mistral(prompt)
                        
                        if result["success"]:
                            st.session_state.ocr_analyse_ia = result["content"]
                            st.rerun()
                        else:
                            st.error(f"❌ Erreur IA : {result['error']}")
            
            # Affichage de l'analyse IA
            if st.session_state.ocr_analyse_ia:
                st.markdown("### 📋 Analyse IA Structurée")
                st.markdown(st.session_state.ocr_analyse_ia)
                
                st.divider()
                
                # Actions
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("💾 Sauvegarder l'analyse", use_container_width=True):
                        sauvegarder_analyse(
                            type_analyse="Facture OCR",
                            resultat=st.session_state.ocr_analyse_ia
                        )
                        st.success("✅ Analyse sauvegardée !")
                
                with col2:
                    try:
                        generer_bouton_word("Analyse_Facture", st.session_state.ocr_analyse_ia)
                    except Exception as e:
                        st.error(f"Erreur export : {e}")


# -----------------------------------------------------------------------------
# 3. AUDIT BALANCE
# -----------------------------------------------------------------------------

elif page == "📊 Audit Balance":
    st.title("📊 Audit de Balance")
    st.markdown("Vérification automatique de l'équilibre et cohérence de la balance")
    
    uploaded_file = st.file_uploader("Balance comptable (CSV, XLSX)", type=["csv", "xlsx"])
    
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
            
            st.success(f"✅ Fichier chargé : {len(df)} lignes")
            afficher_stats_rapides(df)
            
            with st.expander("👀 Aperçu des données"):
                st.dataframe(df.head(20))
            
            if st.button("🔍 Lancer l'audit", type="primary"):
                with st.spinner("Analyse en cours..."):
                    st.subheader("📋 Vérifications")
                    
                    if 'Debit' in df.columns and 'Credit' in df.columns:
                        total_debit = df['Debit'].sum()
                        total_credit = df['Credit'].sum()
                        ecart = abs(total_debit - total_credit)
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Débit", f"{total_debit:,.2f} €")
                        with col2:
                            st.metric("Total Crédit", f"{total_credit:,.2f} €")
                        with col3:
                            st.metric("Écart", f"{ecart:,.2f} €", 
                                    delta_color="inverse" if ecart > 0.01 else "normal")
                        
                        if ecart < 0.01:
                            st.success("✅ Balance équilibrée")
                        else:
                            st.error(f"❌ Déséquilibre détecté : {ecart:,.2f} €")
                    
                    st.subheader("🤖 Analyse IA Approfondie")
                    
                    prompt = f"""Analyse cette balance comptable :

Statistiques :
- Nombre de lignes : {len(df)}
- Colonnes : {', '.join(df.columns.tolist())}
- Total Débit : {total_debit if 'Debit' in df.columns else 'N/A'}
- Total Crédit : {total_credit if 'Credit' in df.columns else 'N/A'}

Premiers enregistrements :
{df.head(10).to_string()}

Fournis :
1. Évaluation de la qualité des données
2. Anomalies potentielles
3. Recommandations d'amélioration
4. Points d'attention"""
                    
                    result = appel_mistral(prompt, temperature=0.3)
                    
                    if result["success"]:
                        st.markdown(result["content"])
                        sauvegarder_analyse(type_analyse="Audit Balance", resultat=result["content"])
                        generer_bouton_word("Audit_Balance", result["content"])
                    else:
                        st.error(f"Erreur IA : {result['error']}")
                        
        except Exception as e:
            st.error(f"❌ Erreur : {str(e)}")


# -----------------------------------------------------------------------------
# 4. TRAITEMENT FEC
# -----------------------------------------------------------------------------

elif page == "📂 Traitement FEC":
    st.title("📂 Traitement FEC")
    st.markdown("Validation et analyse des Fichiers des Écritures Comptables (FEC)")
    
    uploaded_file = st.file_uploader("Fichier FEC (TXT, CSV)", type=["txt", "csv"])
    
    if uploaded_file:
        try:
            try:
                df = pd.read_csv(uploaded_file, sep='|', encoding='utf-8')
            except:
                df = pd.read_csv(uploaded_file, sep='\t', encoding='utf-8')
            
            st.success(f"✅ FEC chargé : {len(df):,} écritures")
            afficher_stats_rapides(df)
            
            with st.expander("👀 Aperçu du FEC"):
                st.dataframe(df.head(20))
            
            if st.button("✅ Valider le FEC", type="primary"):
                with st.spinner("Validation en cours..."):
                    resultats_validation = valider_fec(df)
                    
                    st.subheader("📋 Résultats de validation")
                    
                    for verif, status in resultats_validation.items():
                        if status["valide"]:
                            st.success(f"✅ {verif}")
                        else:
                            st.error(f"❌ {verif} : {status.get('message', '')}")
                    
                    st.subheader("🔍 Analyse FEC")
                    analyse = analyser_fec(df)
                    st.write(analyse)
                    
                    sauvegarder_analyse(type_analyse="Validation FEC", resultat=str(resultats_validation))
                    
        except Exception as e:
            st.error(f"❌ Erreur de lecture du FEC : {str(e)}")
            st.info("💡 Le FEC doit être au format pipe (|) ou tabulation, encodé en UTF-8")


# -----------------------------------------------------------------------------
# 5. LOI DE BENFORD
# -----------------------------------------------------------------------------

elif page == "🛡️ Loi de Benford":
    st.title("🛡️ Audit de Fraude - Loi de Benford")
    st.markdown("Détection statistique d'anomalies et manipulations de données")
    
    uploaded_file = st.file_uploader("Données comptables (CSV, XLSX)", type=["csv", "xlsx"])
    
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
            
            st.success(f"✅ Fichier chargé : {len(df):,} lignes")
            
            col = st.selectbox("Sélectionnez la colonne des montants", df.columns)
            
            if st.button("🔍 Lancer l'audit statistique", type="primary"):
                with st.spinner("Analyse en cours..."):
                    try:
                        fig, rapport, score_risque = analyse_benford_complete(df, col)
                        
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                            st.markdown(rapport)
                            
                            if score_risque == "Élevé":
                                st.error("🚨 ALERTE : Risque élevé de manipulation détecté")
                            elif score_risque == "Modéré":
                                st.warning("⚠️ Attention : Écarts statistiques suspects")
                            else:
                                st.success("✅ Données conformes à la loi de Benford")
                            
                            sauvegarder_analyse(type_analyse="Loi de Benford", resultat=rapport)
                        else:
                            st.error(rapport)
                            
                    except Exception as e:
                        st.error(f"❌ Erreur : {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
                        
        except Exception as e:
            st.error(f"❌ Erreur : {str(e)}")


# -----------------------------------------------------------------------------
# 6. COMPTE DE RÉSULTAT
# -----------------------------------------------------------------------------

elif page == "📈 Compte de Résultat":
    st.title("📈 Compte de Résultat")
    st.markdown("Génération automatique du compte de résultat depuis le FEC")
    
    uploaded_file = st.file_uploader("Fichier FEC ou Balance (CSV, XLSX, TXT)", type=["csv", "xlsx", "txt"])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('xlsx'):
                df = pd.read_excel(uploaded_file)
            elif uploaded_file.name.endswith('txt'):
                df = pd.read_csv(uploaded_file, sep='|', encoding='utf-8')
            else:
                df = pd.read_csv(uploaded_file)
            
            st.success(f"✅ Fichier chargé : {len(df):,} lignes")
            
            col1, col2 = st.columns(2)
            with col1:
                date_debut = st.date_input("Date de début")
            with col2:
                date_fin = st.date_input("Date de fin")
            
            if st.button("📊 Générer le Compte de Résultat", type="primary"):
                with st.spinner("Génération en cours..."):
                    try:
                        resultat = generer_compte_resultat(df, date_debut, date_fin)
                        
                        st.subheader("📈 Compte de Résultat")
                        st.dataframe(resultat, use_container_width=True)
                        
                        if 'Montant' in resultat.columns:
                            total_produits = resultat[resultat['Type'] == 'Produits']['Montant'].sum()
                            total_charges = resultat[resultat['Type'] == 'Charges']['Montant'].sum()
                            resultat_net = total_produits - total_charges
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Total Produits", f"{total_produits:,.2f} €")
                            with col2:
                                st.metric("Total Charges", f"{total_charges:,.2f} €")
                            with col3:
                                st.metric("Résultat Net", f"{resultat_net:,.2f} €",
                                        delta_color="normal" if resultat_net > 0 else "inverse")
                        
                        sauvegarder_analyse(type_analyse="Compte de Résultat", resultat=resultat.to_string())
                        
                    except Exception as e:
                        st.error(f"❌ Erreur : {str(e)}")
                        
        except Exception as e:
            st.error(f"❌ Erreur de chargement : {str(e)}")


# -----------------------------------------------------------------------------
# 7. BILAN COMPTABLE
# -----------------------------------------------------------------------------

elif page == "📊 Bilan Comptable":
    st.title("📊 Bilan Comptable")
    st.markdown("Génération automatique du bilan depuis le FEC")
    
    uploaded_file = st.file_uploader("Fichier FEC ou Balance (CSV, XLSX, TXT)", type=["csv", "xlsx", "txt"])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('xlsx'):
                df = pd.read_excel(uploaded_file)
            elif uploaded_file.name.endswith('txt'):
                df = pd.read_csv(uploaded_file, sep='|', encoding='utf-8')
            else:
                df = pd.read_csv(uploaded_file)
            
            st.success(f"✅ Fichier chargé : {len(df):,} lignes")
            
            date_cloture = st.date_input("Date de clôture")
            
            if st.button("📊 Générer le Bilan", type="primary"):
                with st.spinner("Génération en cours..."):
                    try:
                        bilan = generer_bilan(df, date_cloture)
                        
                        st.subheader("📊 Bilan Comptable")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("### ACTIF")
                            st.dataframe(bilan['actif'], use_container_width=True)
                            total_actif = bilan['actif']['Montant'].sum()
                            st.metric("Total Actif", f"{total_actif:,.2f} €")
                        
                        with col2:
                            st.markdown("### PASSIF")
                            st.dataframe(bilan['passif'], use_container_width=True)
                            total_passif = bilan['passif']['Montant'].sum()
                            st.metric("Total Passif", f"{total_passif:,.2f} €")
                        
                        ecart = abs(total_actif - total_passif)
                        if ecart < 0.01:
                            st.success("✅ Bilan équilibré")
                        else:
                            st.error(f"❌ Déséquilibre : {ecart:,.2f} €")
                        
                        sauvegarder_analyse(type_analyse="Bilan", resultat=f"Actif: {total_actif}, Passif: {total_passif}")
                        
                    except Exception as e:
                        st.error(f"❌ Erreur : {str(e)}")
                        
        except Exception as e:
            st.error(f"❌ Erreur de chargement : {str(e)}")


# -----------------------------------------------------------------------------
# 8. RAPPROCHEMENT BANCAIRE
# -----------------------------------------------------------------------------

elif page == "🔄 Rapprochement Bancaire":
    st.title("🔄 Rapprochement Bancaire")
    st.markdown("Rapprochement automatique entre relevé bancaire et écritures comptables")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📥 Relevé Bancaire")
        releve = st.file_uploader("Relevé bancaire (CSV, XLSX)", type=["csv", "xlsx"], key="releve")
    
    with col2:
        st.subheader("📚 Écritures Comptables")
        ecritures = st.file_uploader("Écritures comptables (CSV, XLSX)", type=["csv", "xlsx"], key="ecritures")
    
    if releve and ecritures:
        try:
            df_releve = pd.read_excel(releve) if releve.name.endswith('xlsx') else pd.read_csv(releve)
            df_ecritures = pd.read_excel(ecritures) if ecritures.name.endswith('xlsx') else pd.read_csv(ecritures)
            
            st.success(f"✅ Relevé : {len(df_releve)} opérations | Écritures : {len(df_ecritures)} lignes")
            
            if st.button("🔄 Lancer le rapprochement", type="primary"):
                with st.spinner("Rapprochement en cours..."):
                    try:
                        resultats = rapprocher_bancaire(df_releve, df_ecritures)
                        
                        st.subheader("📊 Résultats du Rapprochement")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Rapprochés", resultats['nb_rapproches'])
                        with col2:
                            st.metric("Non rapprochés", resultats['nb_non_rapproches'])
                        with col3:
                            taux = (resultats['nb_rapproches'] / len(df_releve) * 100) if len(df_releve) > 0 else 0
                            st.metric("Taux", f"{taux:.1f}%")
                        
                        with st.expander("✅ Opérations rapprochées"):
                            st.dataframe(resultats['rapproches'])
                        
                        with st.expander("❌ Opérations non rapprochées"):
                            st.dataframe(resultats['non_rapproches'])
                        
                        sauvegarder_analyse(type_analyse="Rapprochement Bancaire", resultat=f"Taux: {taux:.1f}%")
                        
                    except Exception as e:
                        st.error(f"❌ Erreur : {str(e)}")
                        
        except Exception as e:
            st.error(f"❌ Erreur de chargement : {str(e)}")


# -----------------------------------------------------------------------------
# 9. RAPPORT CLIENT
# -----------------------------------------------------------------------------

elif page == "📋 Rapport Client":
    st.title("📋 Rapport Client")
    st.markdown("Génération de rapports personnalisés pour vos clients")
    
    st.subheader("👤 Informations Client")
    col1, col2 = st.columns(2)
    
    with col1:
        nom_client = st.text_input("Nom du client")
        siret = st.text_input("SIRET")
    
    with col2:
        periode = st.selectbox("Période", ["Mensuel", "Trimestriel", "Annuel"])
        exercice = st.number_input("Exercice", min_value=2020, max_value=2030, value=2026)
    
    st.subheader("📂 Données Comptables")
    uploaded_file = st.file_uploader("FEC ou Balance (CSV, XLSX)", type=["csv", "xlsx"])
    
    if uploaded_file and nom_client:
        try:
            df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
            
            if st.button("📋 Générer le Rapport", type="primary"):
                with st.spinner("Génération du rapport..."):
                    try:
                        rapport = generer_rapport_client(
                            nom_client=nom_client,
                            siret=siret,
                            periode=periode,
                            exercice=exercice,
                            donnees=df
                        )
                        
                        st.markdown("### 📄 Rapport Généré")
                        st.markdown(rapport)
                        
                        generer_bouton_word(f"Rapport_{nom_client}_{periode}", rapport)
                        sauvegarder_analyse(type_analyse="Rapport Client", resultat=rapport)
                        
                    except Exception as e:
                        st.error(f"❌ Erreur : {str(e)}")
                        
        except Exception as e:
            st.error(f"❌ Erreur : {str(e)}")


# -----------------------------------------------------------------------------
# 10. ALERTES & ANOMALIES
# -----------------------------------------------------------------------------

elif page == "⚠️ Alertes & Anomalies":
    st.title("⚠️ Alertes & Anomalies")
    st.markdown("Détection automatique d'anomalies et situations à risque")
    
    uploaded_file = st.file_uploader("Données comptables (CSV, XLSX, FEC)", type=["csv", "xlsx", "txt"])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('xlsx'):
                df = pd.read_excel(uploaded_file)
            elif uploaded_file.name.endswith('txt'):
                df = pd.read_csv(uploaded_file, sep='|', encoding='utf-8')
            else:
                df = pd.read_csv(uploaded_file)
            
            st.success(f"✅ Fichier chargé : {len(df):,} lignes")
            
            if st.button("🔍 Détecter les anomalies", type="primary"):
                with st.spinner("Analyse en cours..."):
                    try:
                        alertes = detecter_alertes(df)
                        
                        if alertes:
                            st.subheader("🚨 Alertes Détectées")
                            
                            nb_critique = len([a for a in alertes if a['niveau'] == 'CRITIQUE'])
                            nb_warning = len([a for a in alertes if a['niveau'] == 'WARNING'])
                            nb_info = len([a for a in alertes if a['niveau'] == 'INFO'])
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("🔴 Critiques", nb_critique)
                            with col2:
                                st.metric("🟡 Warnings", nb_warning)
                            with col3:
                                st.metric("🔵 Infos", nb_info)
                            
                            for alerte in alertes:
                                if alerte['niveau'] == 'CRITIQUE':
                                    st.error(f"🔴 **{alerte['titre']}** : {alerte['message']}")
                                elif alerte['niveau'] == 'WARNING':
                                    st.warning(f"🟡 **{alerte['titre']}** : {alerte['message']}")
                                else:
                                    st.info(f"🔵 **{alerte['titre']}** : {alerte['message']}")
                            
                            sauvegarder_analyse(type_analyse="Alertes", resultat=str(alertes))
                        else:
                            st.success("✅ Aucune anomalie détectée")
                            
                    except Exception as e:
                        st.error(f"❌ Erreur : {str(e)}")
                        
        except Exception as e:
            st.error(f"❌ Erreur : {str(e)}")


# -----------------------------------------------------------------------------
# 11. COHÉRENCE DES DONNÉES
# -----------------------------------------------------------------------------

elif page == "✅ Cohérence des Données":
    st.title("✅ Cohérence des Données")
    st.markdown("Vérification de la cohérence et de la qualité des données comptables")
    
    uploaded_file = st.file_uploader("Données comptables (CSV, XLSX, FEC)", type=["csv", "xlsx", "txt"])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('xlsx'):
                df = pd.read_excel(uploaded_file)
            elif uploaded_file.name.endswith('txt'):
                df = pd.read_csv(uploaded_file, sep='|', encoding='utf-8')
            else:
                df = pd.read_csv(uploaded_file)
            
            st.success(f"✅ Fichier chargé : {len(df):,} lignes")
            afficher_stats_rapides(df)
            
            if st.button("🔍 Vérifier la cohérence", type="primary"):
                with st.spinner("Vérification en cours..."):
                    try:
                        resultats = verifier_coherence(df)
                        
                        st.subheader("📊 Résultats de Vérification")
                        
                        score_qualite = resultats.get('score_qualite', 0)
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Score Qualité", f"{score_qualite}%",
                                    delta_color="normal" if score_qualite > 80 else "inverse")
                        with col2:
                            st.metric("Champs valides", f"{resultats.get('champs_valides', 0)}/{len(df.columns)}")
                        with col3:
                            st.metric("Lignes complètes", f"{resultats.get('lignes_completes', 0)}/{len(df)}")
                        
                        for check, details in resultats.get('verifications', {}).items():
                            if details['status'] == 'OK':
                                st.success(f"✅ {check} : {details['message']}")
                            elif details['status'] == 'WARNING':
                                st.warning(f"⚠️ {check} : {details['message']}")
                            else:
                                st.error(f"❌ {check} : {details['message']}")
                        
                        if resultats.get('recommandations'):
                            st.subheader("💡 Recommandations")
                            for reco in resultats['recommandations']:
                                st.info(reco)
                        
                        sauvegarder_analyse(type_analyse="Cohérence", resultat=str(resultats))
                        
                    except Exception as e:
                        st.error(f"❌ Erreur : {str(e)}")
                        
        except Exception as e:
            st.error(f"❌ Erreur : {str(e)}")


# -----------------------------------------------------------------------------
# 12. VEILLE FISCALE
# -----------------------------------------------------------------------------

elif page == "📰 Veille Fiscale":
    st.title("📰 Veille Fiscale")
    st.markdown("Dernières actualités fiscales et réglementaires")
    
    if st.button("🔄 Actualiser la veille", type="primary"):
        with st.spinner("Récupération des actualités..."):
            try:
                actualites = obtenir_veille_fiscale()
                
                if actualites:
                    st.subheader("📰 Dernières Actualités")
                    
                    for article in actualites:
                        with st.expander(f"📄 {article['titre']}"):
                            st.caption(f"🗓️ {article.get('date', 'Date inconnue')}")
                            st.markdown(article.get('resume', ''))
                            if article.get('lien'):
                                st.markdown(f"[🔗 Lire l'article complet]({article['lien']})")
                    
                    sauvegarder_analyse(type_analyse="Veille Fiscale", resultat=str(actualites))
                else:
                    st.info("ℹ️ Aucune actualité récente disponible")
                    
            except Exception as e:
                st.error(f"❌ Erreur : {str(e)}")
    
    st.divider()
    st.subheader("❓ Poser une question fiscale")
    
    question = st.text_area("Votre question sur la fiscalité française")
    
    if st.button("🤖 Obtenir une réponse IA") and question:
        with st.spinner("Recherche en cours..."):
            prompt = f"""En tant qu'expert fiscal français, réponds à cette question :

{question}

Fournis :
1. Une réponse claire et précise
2. Les références légales (CGI, BOFiP, etc.)
3. Des exemples si pertinent
4. Les points d'attention"""
            
            result = appel_mistral(prompt, temperature=0.2)
            
            if result["success"]:
                st.markdown("### 💡 Réponse")
                st.markdown(result["content"])
                sauvegarder_analyse(type_analyse="Question Fiscale", resultat=result["content"])
            else:
                st.error(f"❌ Erreur : {result['error']}")


# =============================================================================
# FOOTER
# =============================================================================

st.divider()
st.caption("""
**SMD Consulting** - Superviseur IA Comptable  
Comptable Augmenté par Intelligence Artificielle  
© 2026 - Souleymane Diallo
""")