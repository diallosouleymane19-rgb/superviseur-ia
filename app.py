import streamlit as st
import pandas as pd
from utils.ocr import ocr_image_mistral
from utils.compta_auto import analyse_balance_ai
from utils.fec import traiter_fec
from utils.ai import appel_mistral, extraire_contenu_mistral

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
        "Traitement FEC",
        "Traitement Factures"
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
        st.text_area("", texte, height=200)

        st.subheader("Analyse IA de la facture :")
        prompt = f"""
Tu es un expert-comptable français. Analyse cette facture extraite par OCR :

{texte}

Extrais et structure les informations suivantes :
- Fournisseur (nom, adresse, pays)
- Client (nom, adresse)
- Numéro de facture
- Date de facture
- Montant HT
- TVA
- Montant TTC
- Mode de paiement
- Observations comptables importantes

Réponds de façon claire et structurée.
        """
        analyse = appel_mistral(prompt)
        st.markdown(analyse, unsafe_allow_html=True)

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
                resultat = analyse_balance_ai(df)
                texte_ia = resultat
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
        st.markdown(resultat, unsafe_allow_html=True)

# ---------------------------------------------------------
# PAGE : TRAITEMENT FACTURES EXCEL/CSV
# ---------------------------------------------------------
elif page == "Traitement Factures":
    st.title("Traitement Factures Excel / CSV")
    fichier = st.file_uploader("Importer un fichier de factures (Excel ou CSV)", type=["xlsx", "csv"])
    if fichier:
        try:
            if fichier.name.endswith(".csv"):
                df = pd.read_csv(fichier)
            else:
                df = pd.read_excel(fichier)

            st.subheader("Aperçu des factures :")
            st.dataframe(df)

            # --- STATISTIQUES RAPIDES ---
            st.subheader("Statistiques rapides :")
            col1, col2, col3 = st.columns(3)

            # Cherche une colonne montant
            col_montant = None
            for col in df.columns:
                if any(mot in col.lower() for mot in ["montant", "total", "amount", "prix", "ttc", "ht"]):
                    col_montant = col
                    break

            if col_montant:
                df[col_montant] = pd.to_numeric(df[col_montant], errors="coerce")
                col1.metric("Total", f"{df[col_montant].sum():,.2f} €")
                col2.metric("Moyenne", f"{df[col_montant].mean():,.2f} €")
                col3.metric("Nombre de factures", len(df))
            else:
                st.info("Aucune colonne montant détectée automatiquement.")
                col3.metric("Nombre de factures", len(df))

            if st.button("Analyser les factures"):
                st.info("Analyse IA en cours…")

                apercu = df.head(50).to_string()

                prompt = f"""
Tu es un expert-comptable français. Analyse ce tableau de factures :

{apercu}

Donne une analyse complète et structurée comprenant :

1. RÉSUMÉ GÉNÉRAL
   - Nombre total de factures
   - Montant total, moyen, min et max
   - Principaux fournisseurs ou clients

2. DÉTECTION D'ANOMALIES
   - Doublons potentiels (même montant, même date, même fournisseur)
   - Montants suspects ou inhabituels
   - Factures incomplètes ou mal renseignées

3. ANALYSE PAR PÉRIODE
   - Répartition mensuelle ou trimestrielle si dates disponibles
   - Tendances observées

4. RAPPROCHEMENT COMPTABLE
   - Cohérence des montants HT, TVA, TTC
   - Vérification des équilibres débit/crédit si disponibles
   - Comptes comptables suggérés

5. RECOMMANDATIONS
   - Actions correctives à mener
   - Risques fiscaux identifiés
   - Bonnes pratiques à adopter

Réponds de façon claire, structurée et professionnelle.
                """

                analyse = appel_mistral(prompt)
                st.subheader("Analyse IA :")
                st.markdown(analyse, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier : {e}")