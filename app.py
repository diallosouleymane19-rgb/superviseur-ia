import streamlit as st
import pandas as pd

from utils.ocr import ocr_image_mistral
from utils.compta_auto import analyse_balance_ai
from utils.fec import traiter_fec
from utils.ai import extraire_contenu_mistral


# ---------------------------------------------------------
# STYLE GLOBAL (CSS)
# ---------------------------------------------------------
st.markdown("""
<style>
table {
    width: 100%;
    border-collapse: collapse;
}
th, td {
    border: 1px solid #ddd;
    padding: 6px;
}
th {
    background-color: #f5f5f5;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# MENU LATÉRAL
# ---------------------------------------------------------
st.sidebar.title("Superviseur IA Comptable")
page = st.sidebar.radio(
    "Navigation",
    [
        "Accueil",
        "OCR Facture",
        "Analyse Balance",
        "Traitement FEC"
    ]
)


# ---------------------------------------------------------
# PAGE : ACCUEIL
# ---------------------------------------------------------
if page == "Accueil":
    st.title("Superviseur IA Comptable")
    st.write("Bienvenue dans votre assistant comptable intelligent.")


# ---------------------------------------------------------
# PAGE : OCR FACTURE
# ---------------------------------------------------------
elif page == "OCR Facture":
    st.title("OCR Facture (IA Vision)")

    fichier = st.file_uploader("Importer une facture (PDF ou image)", type=["pdf", "png", "jpg", "jpeg"])

    if fichier:
        st.info("Analyse en cours…")
        texte = ocr_image_mistral(fichier)
        st.subheader("Texte extrait :")
        st.markdown(texte, unsafe_allow_html=True)


# ---------------------------------------------------------
# PAGE : ANALYSE BALANCE
# ---------------------------------------------------------
elif page == "Analyse Balance":
    st.title("Analyse de la Balance Comptable")

    fichier = st.file_uploader("Importer une balance (Excel ou CSV)", type=["xlsx", "csv"])

    if fichier:
        try:
            if fichier.name.endswith(".csv"):
                df = pd.read_csv(fichier)
            else:
                df = pd.read_excel(fichier)

            st.subheader("Aperçu de la balance :")
            st.dataframe(df)

            if st.button("Analyser la balance"):
                st.info("Analyse IA en cours…")

                # Appel IA
                resultat = analyse_balance_ai(df)
                texte_ia = extraire_contenu_mistral(resultat)

                st.subheader("Analyse IA :")
                st.markdown(texte_ia, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier : {e}")


# ---------------------------------------------------------
# PAGE : TRAITEMENT FEC
# ---------------------------------------------------------
elif page == "Traitement FEC":
    st.title("Traitement FEC")

    fichier = st.file_uploader("Importer un fichier FEC", type=["txt"])

    if fichier:
        st.info("Traitement en cours…")
        resultat = traiter_fec(fichier)
        st.subheader("Résultat :")
        st.write(resultat)
