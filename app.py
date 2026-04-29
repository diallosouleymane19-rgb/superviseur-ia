import streamlit as st
import pandas as pd
from utils.ocr import ocr_image_mistral
from utils.compta_auto import analyse_balance_ai
from utils.fec import traiter_fec
from utils.ai import appel_mistral, extraire_contenu_mistral
from utils.rapprochement import rapprocher_banque_compta
from utils.coherence import analyser_coherence
from utils.alertes import analyser_alertes
from utils.veille_fiscale import obtenir_veille_fiscale

# ---------------------------------------------------------
# STYLE GLOBAL (CSS)
# ---------------------------------------------------------
st.markdown("""
<style>
body {
    font-family: 'Segoe UI', sans-serif;
}
table {
    width: 100%;
    border-collapse: collapse;
}
th, td {
    border: 1px solid #ddd;
    padding: 8px;
}
th {
    background-color: #1f77b4;
    color: white;
    font-weight: bold;
}
tr:nth-child(even) {
    background-color: #f9f9f9;
}
.metric-container {
    background-color: #f0f4ff;
    padding: 10px;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# MENU LATÉRAL
# ---------------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/96/accounting.png", width=80)
st.sidebar.title("Superviseur IA Comptable")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Accueil",
        "🧾 OCR Facture",
        "📊 Analyse Balance",
        "📂 Traitement FEC",
        "💳 Traitement Factures",
        "🏦 Rapprochement Bancaire",
        "🔗 Cohérence Inter-Documents",
        "🚨 Alertes de Gestion",
        "📰 Veille Fiscale"
    ]
)

# ---------------------------------------------------------
# PAGE : ACCUEIL
# ---------------------------------------------------------
if page == "🏠 Accueil":
    st.title("🏠 Superviseur IA Comptable")
    st.markdown("### Bienvenue dans votre assistant comptable intelligent")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    col1.info("🧾 OCR Facture\nExtraction automatique de vos factures")
    col2.info("📊 Analyse Balance\nAnalyse IA de votre balance comptable")
    col3.info("📂 Traitement FEC\nContrôle fiscal de vos écritures")

    st.markdown("---")
    col4, col5, col6 = st.columns(3)
    col4.success("🏦 Rapprochement Bancaire\nComparez banque et comptabilité")
    col5.success("🔗 Cohérence Inter-Documents\nCroisez vos documents comptables")
    col6.success("🚨 Alertes de Gestion\nDétectez les anomalies en temps réel")

    st.markdown("---")
    st.warning("📰 Veille Fiscale — Restez à jour sur la réglementation française")

# ---------------------------------------------------------
# PAGE : OCR FACTURE
# ---------------------------------------------------------
elif page == "🧾 OCR Facture":
    st.title("🧾 OCR Facture (IA Vision)")
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
- Compte comptable suggéré
- Observations comptables importantes

Réponds de façon claire et structurée.
        """
        analyse = appel_mistral(prompt)
        st.markdown(analyse, unsafe_allow_html=True)

# ---------------------------------------------------------
# PAGE : ANALYSE BALANCE
# ---------------------------------------------------------
elif page == "📊 Analyse Balance":
    st.title("📊 Analyse de la Balance Comptable")
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
                st.subheader("Analyse IA :")
                st.markdown(resultat, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier : {e}")

# ---------------------------------------------------------
# PAGE : TRAITEMENT FEC
# ---------------------------------------------------------
elif page == "📂 Traitement FEC":
    st.title("📂 Traitement FEC")
    fichier = st.file_uploader("Importer un fichier FEC", type=["txt"])
    if fichier:
        st.info("Traitement en cours…")
        resultat = traiter_fec(fichier)
        st.subheader("Résultat :")
        st.markdown(resultat, unsafe_allow_html=True)

# ---------------------------------------------------------
# PAGE : TRAITEMENT FACTURES
# ---------------------------------------------------------
elif page == "💳 Traitement Factures":
    st.title("💳 Traitement Factures Excel / CSV")
    fichier = st.file_uploader("Importer un fichier de factures", type=["xlsx", "csv"])
    if fichier:
        try:
            if fichier.name.endswith(".csv"):
                df = pd.read_csv(fichier)
            else:
                df = pd.read_excel(fichier)

            st.subheader("Aperçu des factures :")
            st.dataframe(df)

            col1, col2, col3 = st.columns(3)
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
                col3.metric("Nombre de factures", len(df))

            if st.button("Analyser les factures"):
                st.info("Analyse IA en cours…")
                apercu = df.head(50).to_string()
                prompt = f"""
Tu es un expert-comptable français. Analyse ce tableau de factures :

{apercu}

Donne une analyse complète :
1. RÉSUMÉ GÉNÉRAL
2. DÉTECTION D'ANOMALIES
3. ANALYSE PAR PÉRIODE
4. RAPPROCHEMENT COMPTABLE
5. RECOMMANDATIONS

Réponds de façon claire et professionnelle.
                """
                analyse = appel_mistral(prompt)
                st.subheader("Analyse IA :")
                st.markdown(analyse, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Erreur : {e}")

# ---------------------------------------------------------
# PAGE : RAPPROCHEMENT BANCAIRE
# ---------------------------------------------------------
elif page == "🏦 Rapprochement Bancaire":
    st.title("🏦 Rapprochement Bancaire")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Relevé Bancaire")
        fichier_banque = st.file_uploader("Importer le relevé bancaire", type=["xlsx", "csv"], key="banque")

    with col2:
        st.subheader("Écritures Comptables")
        fichier_compta = st.file_uploader("Importer les écritures comptables", type=["xlsx", "csv"], key="compta")

    if fichier_banque and fichier_compta:
        try:
            df_banque = pd.read_csv(fichier_banque) if fichier_banque.name.endswith(".csv") else pd.read_excel(fichier_banque)
            df_compta = pd.read_csv(fichier_compta) if fichier_compta.name.endswith(".csv") else pd.read_excel(fichier_compta)

            st.subheader("Aperçu Relevé Bancaire :")
            st.dataframe(df_banque)

            st.subheader("Aperçu Écritures Comptables :")
            st.dataframe(df_compta)

            if st.button("Lancer le rapprochement"):
                st.info("Rapprochement en cours…")
                resultat = rapprocher_banque_compta(df_banque, df_compta)
                st.subheader("Résultat du rapprochement :")
                st.markdown(resultat, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Erreur : {e}")

# ---------------------------------------------------------
# PAGE : COHÉRENCE INTER-DOCUMENTS
# ---------------------------------------------------------
elif page == "🔗 Cohérence Inter-Documents":
    st.title("🔗 Cohérence Inter-Documents")
    st.info("Importez un ou plusieurs documents pour analyser leur cohérence.")

    fichier_factures = st.file_uploader("Factures (optionnel)", type=["xlsx", "csv"], key="fact")
    fichier_balance = st.file_uploader("Balance (optionnel)", type=["xlsx", "csv"], key="bal")
    fichier_fec = st.file_uploader("FEC (optionnel)", type=["txt"], key="fec")

    if st.button("Analyser la cohérence"):
        df_factures = df_balance = df_fec = None

        if fichier_factures:
            df_factures = pd.read_csv(fichier_factures) if fichier_factures.name.endswith(".csv") else pd.read_excel(fichier_factures)
        if fichier_balance:
            df_balance = pd.read_csv(fichier_balance) if fichier_balance.name.endswith(".csv") else pd.read_excel(fichier_balance)
        if fichier_fec:
            df_fec = pd.read_csv(fichier_fec, sep="\t", dtype=str)

        if df_factures is None and df_balance is None and df_fec is None:
            st.warning("Veuillez importer au moins un document.")
        else:
            st.info("Analyse en cours…")
            resultat = analyser_coherence(df_factures, df_balance, df_fec)
            st.subheader("Résultat :")
            st.markdown(resultat, unsafe_allow_html=True)

# ---------------------------------------------------------
# PAGE : ALERTES DE GESTION
# ---------------------------------------------------------
elif page == "🚨 Alertes de Gestion":
    st.title("🚨 Alertes de Gestion")
    fichier = st.file_uploader("Importer un fichier financier (Excel ou CSV)", type=["xlsx", "csv"])
    if fichier:
        try:
            df = pd.read_csv(fichier) if fichier.name.endswith(".csv") else pd.read_excel(fichier)
            st.subheader("Aperçu :")
            st.dataframe(df)

            if st.button("Générer les alertes"):
                st.info("Analyse en cours…")
                resultat = analyser_alertes(df)
                st.subheader("Alertes de Gestion :")
                st.markdown(resultat, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Erreur : {e}")

# ---------------------------------------------------------
# PAGE : VEILLE FISCALE
# ---------------------------------------------------------
elif page == "📰 Veille Fiscale":
    st.title("📰 Veille Fiscale")
    st.info("Cliquez sur le bouton pour obtenir la veille fiscale du moment.")

    if st.button("Obtenir la veille fiscale"):
        st.info("Génération en cours…")
        resultat = obtenir_veille_fiscale()
        st.markdown(resultat, unsafe_allow_html=True)