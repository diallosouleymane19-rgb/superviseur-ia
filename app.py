import streamlit as st
import json
import pandas as pd

# Import des modules internes
from utils.database import (
    init_db,
    ajouter_client,
    lister_clients,
    sauvegarder_facture,
    charger_historique,
    vider_historique
)

from utils.ai import (
    appel_mistral,
    extraire_contenu_mistral,
    parse_montant,
    extraire_compte_valide
)

from utils.fec import generer_fec
from utils.ocr import ocr_image_mistral


# ---------------------------------------------------------
# INITIALISATION DE LA BASE DE DONNÉES
# ---------------------------------------------------------
init_db()

st.set_page_config(page_title="Superviseur IA Comptable", layout="wide")
st.title("🧠 Superviseur IA Comptable")
st.write("Analyse automatique des factures, génération FEC, OCR et gestion clients.")


# ---------------------------------------------------------
# MENU LATÉRAL
# ---------------------------------------------------------
menu = st.sidebar.selectbox(
    "Navigation",
    ["Accueil", "Clients", "Analyse facture", "OCR", "Historique", "Générer FEC"]
)


# ---------------------------------------------------------
# PAGE : ACCUEIL
# ---------------------------------------------------------
if menu == "Accueil":
    st.subheader("Bienvenue dans le Superviseur IA Comptable")
    st.write("Choisissez une fonctionnalité dans le menu à gauche.")


# ---------------------------------------------------------
# PAGE : CLIENTS
# ---------------------------------------------------------
elif menu == "Clients":
    st.subheader("Gestion des clients")

    with st.form("form_client"):
        nom = st.text_input("Nom du client")
        adresse = st.text_input("Adresse")
        siret = st.text_input("SIRET")
        submit = st.form_submit_button("Ajouter")

        if submit:
            ajouter_client(nom, adresse, siret)
            st.success("Client ajouté avec succès.")

    st.write("### Liste des clients")
    clients = lister_clients()
    st.dataframe(pd.DataFrame(clients, columns=["Nom", "Adresse", "SIRET"]))


# ---------------------------------------------------------
# PAGE : ANALYSE FACTURE
# ---------------------------------------------------------
elif menu == "Analyse facture":
    st.subheader("Analyse automatique d'une facture")

    uploaded_file = st.file_uploader("Importer une facture (PDF ou image)", type=["pdf", "png", "jpg", "jpeg"])

    if uploaded_file:
        st.info("Analyse en cours…")

        contenu = ocr_image_mistral(uploaded_file)
        st.write("### Contenu extrait :")
        st.write(contenu)

        analyse = appel_mistral(contenu)
        st.write("### Analyse IA :")
        st.write(analyse)

        montant = parse_montant(analyse)
        compte = extraire_compte_valide(analyse)

        sauvegarder_facture(contenu, analyse, montant, compte)
        st.success("Facture analysée et sauvegardée.")


# ---------------------------------------------------------
# PAGE : OCR
# ---------------------------------------------------------
elif menu == "OCR":
    st.subheader("Extraction OCR")

    uploaded_file = st.file_uploader("Importer une image", type=["png", "jpg", "jpeg"])

    if uploaded_file:
        texte = ocr_image_mistral(uploaded_file)
        st.write("### Texte extrait :")
        st.write(texte)


# ---------------------------------------------------------
# PAGE : HISTORIQUE
# ---------------------------------------------------------
elif menu == "Historique":
    st.subheader("Historique des analyses")

    historique = charger_historique()

    if historique:
        st.dataframe(pd.DataFrame(historique))
    else:
        st.info("Aucune analyse enregistrée.")

    if st.button("Vider l'historique"):
        vider_historique()
        st.success("Historique supprimé.")


# ---------------------------------------------------------
# PAGE : GÉNÉRER FEC
# ---------------------------------------------------------
elif menu == "Générer FEC":
    st.subheader("Génération du FEC")

    if st.button("Générer le fichier FEC"):
        fec_path = generer_fec()
        st.success(f"FEC généré : {fec_path}")
        st.download_button("Télécharger le FEC", data=open(fec_path, "rb"), file_name="FEC.txt")
