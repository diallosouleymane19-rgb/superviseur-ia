import streamlit as st
import json
import pandas as pd
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
st.write("Analyse automatique des factures, génération FEC, OCR, veille fiscale et gestion clients.")


# ---------------------------------------------------------
# MENU LATÉRAL
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
        "Analyse de la balance"
    ]
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


# ---------------------------------------------------------
# PAGE : VEILLE FISCALE
# ---------------------------------------------------------
elif menu == "Veille fiscale":
    st.subheader("📰 Veille fiscale automatisée")

    # --- Échéances fiscales automatiques ---
    mois = datetime.datetime.now().strftime("%B %Y")
    st.write(f"### 📅 Échéances fiscales – {mois}")

    echeances = [
        "🔸 **TVA** : Déclaration CA3 – le 19 ou 24",
        "🔸 **TVA** : Régime simplifié – acompte trimestriel",
        "🔸 **DSN** : Déclaration sociale nominative – le 5 ou le 15",
        "🔸 **IS** : Acompte trimestriel – 15 du mois",
        "🔸 **CFE** : Paiement du solde (décembre) ou acompte (juin)",
        "🔸 **CVAE** : Déclaration et paiement si applicable",
        "🔸 **IR** : Retenue à la source – reversement mensuel",
    ]

    for e in echeances:
        st.write(e)

    st.markdown("---")

    # --- Analyse fiscale IA ---
    question = st.text_area("Pose une question fiscale :", height=150)

    if st.button("Analyser la question"):
        if question.strip():
            st.info("Analyse en cours…")

            prompt = f"""
Tu es un fiscaliste français. Réponds clairement et cite les règles applicables.

Question :
{question}

Donne une réponse structurée :
- règle fiscale applicable
- références (CGI, BOFiP si possible)
- risques fiscaux
- conseils pratiques
            """

            reponse = appel_mistral(prompt)

            st.write("### Réponse :")
            st.write(reponse)
        else:
            st.warning("Veuillez entrer une question.")


# ---------------------------------------------------------
# PAGE : ANALYSE DE LA BALANCE
# ---------------------------------------------------------
elif menu == "Analyse de la balance":
    st.subheader("📊 Analyse intelligente de la balance comptable")

    fichier = st.file_uploader("Importer une balance (CSV ou Excel)", type=["csv", "xlsx"])

    if fichier:
        try:
            if fichier.name.endswith(".csv"):
                df = pd.read_csv(fichier)
            else:
                df = pd.read_excel(fichier)

            st.write("### Aperçu de la balance :")
            st.dataframe(df)

            contenu_balance = df.to_csv(index=False)

            if st.button("Analyser la balance"):
                st.info("Analyse IA en cours…")

                prompt = f"""
Tu es un expert-comptable. Analyse cette balance comptable :

{contenu_balance}

Détaille :
- anomalies possibles
- comptes incohérents
- soldes anormaux
- suggestions d'écritures
- risques fiscaux
                """

                analyse = appel_mistral(prompt)

                st.write("### Résultats de l'analyse :")
                st.write(analyse)

        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier : {e}")
