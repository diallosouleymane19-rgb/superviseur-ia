import streamlit as st
import pandas as pd
import json
import datetime

# Import des modules internes
from utils.database import (
    init_db,
    ajouter_client,
    lister_clients,
    sauvegarder_facture,
    charger_historique,
    vider_historique
)

from utils.ocr import ocr_image_mistral
from utils.fec import generer_fec
from utils.ai import appel_mistral

# Initialisation de la base
init_db()

# ---------------------------------------------------------
# CONFIGURATION DE L'APP
# ---------------------------------------------------------
st.set_page_config(
    page_title="Superviseur IA Comptable",
    page_icon="🧠",
    layout="wide"
)

# ---------------------------------------------------------
# MENU
# ---------------------------------------------------------
menu = st.sidebar.selectbox(
    "Navigation",
    [
        "Accueil",
        "Clients",
        "Analyse facture",
        "OCR",
        "Historique",
        "Générer FEC",
        "Veille fiscale",
        "Analyse de la balance",
        "Écriture comptable automatique"
    ]
)

# ---------------------------------------------------------
# PAGE : ACCUEIL
# ---------------------------------------------------------
if menu == "Accueil":
    st.title("🧠 Superviseur IA Comptable")
    st.write("Analyse automatique des factures, génération FEC, OCR, veille fiscale et gestion clients.")
    st.info("Choisissez une fonctionnalité dans le menu à gauche.")

# ---------------------------------------------------------
# PAGE : CLIENTS
# ---------------------------------------------------------
elif menu == "Clients":
    st.subheader("👥 Gestion des clients")

    nom = st.text_input("Nom du client")
    if st.button("Ajouter"):
        ajouter_client(nom)
        st.success("Client ajouté.")

    st.write("### Liste des clients")
    st.table(lister_clients())

# ---------------------------------------------------------
# PAGE : ANALYSE FACTURE
# ---------------------------------------------------------
elif menu == "Analyse facture":
    st.subheader("📄 Analyse automatique de facture")

    fichier = st.file_uploader("Importer une facture", type=["pdf", "png", "jpg", "jpeg"])
    if fichier:
        contenu = ocr_image_mistral(fichier)
        st.write("### Contenu extrait :")
        st.write(contenu)

        if st.button("Analyser avec IA"):
            prompt = f"Analyse cette facture : {contenu}"
            resultat = appel_mistral(prompt)
            st.write("### Analyse IA :")
            st.write(resultat)

# ---------------------------------------------------------
# PAGE : OCR
# ---------------------------------------------------------
elif menu == "OCR":
    st.subheader("🔍 OCR – Extraction de texte")

    fichier = st.file_uploader("Importer un document", type=["pdf", "png", "jpg", "jpeg"])
    if fichier:
        texte = ocr_image_mistral(fichier)
        st.text_area("Texte extrait :", texte, height=300)

# ---------------------------------------------------------
# PAGE : HISTORIQUE
# ---------------------------------------------------------
elif menu == "Historique":
    st.subheader("📚 Historique des analyses")

    st.write("### Factures analysées")
    st.table(charger_historique())

    if st.button("Vider l'historique"):
        vider_historique()
        st.success("Historique supprimé.")

# ---------------------------------------------------------
# PAGE : GÉNÉRER FEC
# ---------------------------------------------------------
elif menu == "Générer FEC":
    st.subheader("📁 Génération FEC")

    fichier = st.file_uploader("Importer un fichier comptable", type=["csv", "xlsx"])
    if fichier:
        df = pd.read_csv(fichier) if fichier.name.endswith(".csv") else pd.read_excel(fichier)
        fec = generer_fec(df)

        st.write("### FEC généré :")
        st.dataframe(fec)

        st.download_button(
            "Télécharger FEC",
            fec.to_csv(index=False),
            file_name="fec.csv"
        )

# ---------------------------------------------------------
# PAGE : VEILLE FISCALE
# ---------------------------------------------------------
elif menu == "Veille fiscale":
    st.subheader("📢 Veille fiscale automatisée")

    question = st.text_input("Posez une question fiscale")
    if st.button("Analyser"):
        prompt = f"Réponds comme un fiscaliste expert : {question}"
        reponse = appel_mistral(prompt)
        st.write("### Réponse IA :")
        st.write(reponse)

# ---------------------------------------------------------
# PAGE : ANALYSE DE LA BALANCE
# ---------------------------------------------------------
elif menu == "Analyse de la balance":
    st.subheader("📊 Analyse IA de la balance comptable")

    fichier = st.file_uploader("Importer une balance", type=["csv", "xlsx"])
    if fichier:
        df = pd.read_csv(fichier) if fichier.name.endswith(".csv") else pd.read_excel(fichier)
        st.write("### Balance importée :")
        st.dataframe(df)

        if st.button("Analyser la balance"):
            prompt = f"Analyse cette balance comptable : {df.to_json()}"
            resultat = appel_mistral(prompt)
            st.write("### Analyse IA :")
            st.write(resultat)

# ---------------------------------------------------------
# PAGE : ÉCRITURE COMPTABLE AUTOMATIQUE (PREMIUM)
# ---------------------------------------------------------
elif menu == "Écriture comptable automatique":
    st.subheader("🧾 Génération automatique d'écriture comptable (Premium)")

    fichier = st.file_uploader("Importer une facture (PDF ou image)", type=["pdf", "png", "jpg", "jpeg"])

    if fichier:
        st.info("Analyse OCR en cours…")
        contenu = ocr_image_mistral(fichier)

        st.write("### Contenu extrait :")
        st.write(contenu)

        if st.button("Générer l'écriture comptable"):
            st.info("Analyse comptable IA en cours…")

            from utils.compta_auto import analyse_facture_premium
            resultat = analyse_facture_premium(contenu)

            st.write("### Résultat structuré :")
            st.json(resultat)

            if "ecriture_comptable" in resultat:
                st.write("### Écriture comptable (format exportable) :")
                df = pd.DataFrame(resultat["ecriture_comptable"])
                st.dataframe(df)

                st.download_button(
                    "Télécharger en CSV",
                    df.to_csv(index=False),
                    file_name="ecriture_comptable.csv"
                )
