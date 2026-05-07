import streamlit as st
import pandas as pd
import os
from utils.ocr import ocr_image_mistral
from utils.ai import appel_mistral, extraire_contenu_mistral
from utils.export_word import export_analyse_word
from auth import login, logout, is_connecte

# 1. Configuration de l'interface
st.set_page_config(page_title="SMD Consulting - Superviseur IA", layout="wide", page_icon="📊")

# Style CSS pour un rendu professionnel
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #1f77b4; color: white; font-weight: bold; }
    .stAlert { border-radius: 10px; }
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# 2. Vérification de la connexion
if not is_connecte():
    login()
    st.stop()

# 3. Menu de navigation
st.sidebar.title("SMD Consulting")
st.sidebar.markdown(f"👤 Expert : **{st.session_state.get('username', 'Utilisateur')}**")
st.sidebar.divider()

page = st.sidebar.radio(
    "Modules de supervision",
    ["🏠 Accueil", "🧾 Analyse Facture (OCR)", "📊 Audit Balance", "📂 Traitement FEC", "🛡️ Loi de Benford", "📰 Veille Fiscale"]
)

st.sidebar.divider()
if st.sidebar.button("🚪 Déconnexion"):
    logout()

# --- FONCTION DE TÉLÉCHARGEMENT SÉCURISÉE ---
def generer_bouton_word(titre, contenu):
    try:
        # On s'assure que le contenu est du texte pur
        texte_final = extraire_contenu_mistral(contenu)
        buf = export_analyse_word(titre, texte_final)
        st.download_button(f"📄 Télécharger le Rapport {titre}", buf, f"{titre}.docx")
    except Exception as e:
        st.error(f"Erreur lors de la préparation du fichier Word : {e}")

# 4. Logique des pages
if page == "🏠 Accueil":
    st.title("🏠 Tableau de bord")
    st.info("Bienvenue dans votre outil de supervision. Sélectionnez un module à gauche pour débuter.")

elif page == "🧾 Analyse Facture (OCR)":
    st.title("🧾 Analyse de Facture")
    f = st.file_uploader("Déposer une facture (PDF, PNG, JPG)", type=["pdf", "png", "jpg"])
    if f:
        with st.spinner("L'IA analyse le document..."):
            texte_ocr = ocr_image_mistral(f)
            analyse = appel_mistral(f"Analyse cette facture (Fournisseur, Date, HT, TVA, TTC) : {texte_ocr}")
            
            if "429" in str(analyse):
                st.warning("⚠️ Le service est momentanément saturé (Erreur 429). Veuillez patienter quelques minutes.")
            else:
                st.markdown(analyse)
                generer_bouton_word("Analyse_Facture", analyse)

elif page == "📊 Audit Balance":
    st.title("📊 Audit de Balance")
    f = st.file_uploader("Balance Excel (.xlsx)", type=["xlsx"])
    if f:
        df = pd.read_excel(f)
        if st.button("Lancer l'analyse IA"):
            with st.spinner("Examen des comptes..."):
                analyse = appel_mistral(f"Analyse cette balance comptable et identifie les anomalies : {df.to_string()[:2000]}")
                st.markdown(analyse)
                generer_bouton_word("Audit_Balance", analyse)

elif page == "🛡️ Loi de Benford":
    st.title("🛡️ Audit de Fraude")
    try:
        from benford_module import analyse_benford_complete
        f = st.file_uploader("Données comptables", type=["csv", "xlsx"])
        if f:
            df = pd.read_excel(f) if f.name.endswith('xlsx') else pd.read_csv(f)
            col = st.selectbox("Sélectionnez la colonne des montants", df.columns)
            if st.button("Lancer l'audit statistique"):
                fig, rapp, risque = analyse_benford_complete(df, col)
                st.plotly_chart(fig)
                st.markdown(rapp)
    except ImportError:
        st.error("Le module Benford est mal configuré. Vérifiez vos fichiers utils.")

elif page == "📰 Veille Fiscale":
    st.title("📰 Dernières Actualités Fiscales")
    if st.button("Actualiser la veille"):
        from utils.veille_fiscale import obtenir_veille_fiscale
        res = obtenir_veille_fiscale()
        if "429" in str(res):
            st.warning("⚠️ Limite de requêtes atteinte. Réessayez dans un instant.")
        else:
            st.markdown(res)
