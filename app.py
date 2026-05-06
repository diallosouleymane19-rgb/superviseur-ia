import streamlit as st
import pandas as pd
from utils.ocr import ocr_image_mistral
from utils.compta_auto import analyse_balance_ai
from utils.fec import traiter_fec
from utils.ai import appel_mistral, extraire_contenu_mistral
from utils.export_word import export_analyse_word
from auth import login, logout, is_connecte

# 1. CONFIGURATION DE LA PAGE
st.set_page_config(
    page_title="SMD Consulting - Superviseur IA",
    page_icon="📊",
    layout="wide"
)

# 2. STYLE PROFESSIONNEL (CSS)
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #1f77b4; color: white; font-weight: bold; }
    .stAlert { border-radius: 10px; }
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# 3. VÉRIFICATION CONNEXION
if not is_connecte():
    login()
    st.stop()

# 4. MENU LATÉRAL
st.sidebar.image("https://img.icons8.com/color/96/accounting.png", width=60)
st.sidebar.title("SMD Consulting")
st.sidebar.markdown(f"👤 Expert : **{st.session_state.get('username', 'Utilisateur')}**")
st.sidebar.divider()

page = st.sidebar.radio(
    "Navigation",
    ["🏠 Accueil", "🧾 Supervision Flux (OCR)", "📊 Audit Balance", "📂 Traitement FEC", "🛡️ Audit Benford"]
)

st.sidebar.divider()
logout()

# ---------------------------------------------------------
# PAGE : ACCUEIL
# ---------------------------------------------------------
if page == "🏠 Accueil":
    st.title("🏠 Superviseur IA Comptable")
    st.markdown("### Bienvenue dans votre cockpit de supervision augmentée.")
    st.info("Sélectionnez un module dans le menu à gauche pour commencer vos analyses.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.success("**Objectif Sécurité** : Détectez les anomalies et les fraudes sur 100% des flux.")
    with col2:
        st.success("**Objectif Productivité** : Automatisez les tâches à faible valeur ajoutée.")

# ---------------------------------------------------------
# PAGE : OCR FACTURE
# ---------------------------------------------------------
elif page == "🧾 Supervision Flux (OCR)":
    st.title("🧾 Analyse de Factures par IA")
    fichier = st.file_uploader("Importer une facture (PDF, JPG, PNG)", type=["pdf", "png", "jpg"])
    
    if fichier:
        with st.spinner("Analyse et extraction des données..."):
            texte_brut = ocr_image_mistral(fichier)
            resultat_ia = appel_mistral(f"Extraire Date, Fournisseur, HT, TVA, TTC et analyser la cohérence : {texte_brut}")
            
            # NETTOYAGE DU CONTENU
            analyse_propre = extraire_contenu_mistral(resultat_ia)
            
            st.divider()
            st.markdown(analyse_propre)
            
            # EXPORT WORD
            buf = export_analyse_word("Rapport d'Analyse Facture", analyse_propre)
            st.download_button("📄 Télécharger le Rapport Word", buf, f"Rapport_Facture_{fichier.name}.docx")

# ---------------------------------------------------------
# PAGE : BALANCE
# ---------------------------------------------------------
elif page == "📊 Audit Balance":
    st.title("📊 Audit IA de la Balance Comptable")
    fichier = st.file_uploader("Importer une Balance (Excel)", type=["xlsx"])
    
    if fichier:
        df = pd.read_excel(fichier)
        if st.button("Lancer l'Audit des Cycles"):
            with st.spinner("L'IA examine les comptes..."):
                resultat_brut = analyse_balance_ai(df)
                analyse_propre = extraire_contenu_mistral(resultat_brut)
                
                st.divider()
                st.markdown(analyse_propre)
                
                buf = export_analyse_word("Audit de Balance Comptable", analyse_propre)
                st.download_button("📄 Télécharger l'Audit Word", buf, "Audit_Balance.docx")

# ---------------------------------------------------------
# PAGE : FEC
# ---------------------------------------------------------
elif page == "📂 Traitement FEC":
    st.title("📂 Contrôle du Fichier des Écritures Comptables")
    fichier = st.file_uploader("Importer un FEC (.txt)", type=["txt"])
    
    if fichier:
        with st.spinner("Vérification de la structure et des écritures..."):
            resultat_brut = traiter_fec(fichier)
            analyse_propre = extraire_contenu_mistral(resultat_brut)
            
            st.divider()
            st.markdown(analyse_propre)
            
            buf = export_analyse_word("Contrôle de Conformité FEC", analyse_propre)
            st.download_button("📄 Télécharger le Rapport FEC", buf, "Rapport_FEC.docx")

# ---------------------------------------------------------
# PAGE : BENFORD
# ---------------------------------------------------------
elif page == "🛡️ Audit Benford":
    st.title("🛡️ Audit de Fraude (Loi de Benford)")
    st.warning("Ce module analyse la probabilité statistique de manipulation des chiffres.")
    # (Logique Benford simplifiée pour l'exemple, à adapter selon votre module spécifique)
    st.info("Veuillez importer un fichier FEC ou une liste de montants pour lancer l'audit statistique.")

