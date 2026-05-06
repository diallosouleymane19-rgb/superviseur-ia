import streamlit as st
import pandas as pd
import base64
from utils.ocr import ocr_image_mistral
from utils.compta_auto import analyse_balance_ai
from utils.fec import traiter_fec
from utils.ai import appel_mistral, extraire_contenu_mistral
from utils.rapprochement import rapprocher_banque_compta
from utils.coherence import analyser_coherence
from utils.alertes import analyser_alertes
from utils.veille_fiscale import obtenir_veille_fiscale
from utils.bilan import analyser_bilan, analyser_bilan_texte
from utils.compte_resultat import analyser_compte_resultat, analyser_cr_texte
from utils.database import init_db, creer_client, lister_clients, supprimer_client, sauvegarder_analyse, lister_analyses, get_analyse, supprimer_analyse
from utils.rapport_client import generer_rapport_client
from utils.export_word import export_analyse_word
from auth import login, logout, is_connecte

# --- NOUVEL IMPORT : MODULE BENFORD ---
from benford_module import analyse_benford_complete

# Initialiser la base de données
init_db()

# ---------------------------------------------------------
# FONCTIONS EXPORT
# ---------------------------------------------------------
def telecharger_analyse(titre, contenu):
    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{titre}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
            h1 {{ color: #1f77b4; border-bottom: 2px solid #1f77b4; padding-bottom: 10px; }}
            pre {{ background: #f5f5f5; padding: 20px; border-radius: 8px; white-space: pre-wrap; }}
        </style>
    </head>
    <body>
        <h1>{titre}</h1>
        <pre>{contenu}</pre>
    </body>
    </html>
    """
    b64 = base64.b64encode(html.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{titre}.html">📥 Télécharger en HTML</a>'
    st.markdown(href, unsafe_allow_html=True)

def telecharger_word(titre, contenu, nom_client="", exercice=""):
    buffer = export_analyse_word(titre, contenu, nom_client, exercice)
    st.download_button(
        label="📄 Télécharger en Word (.docx)",
        data=buffer,
        file_name=f"{titre}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

def telecharger_rapport_html(titre, html_contenu):
    b64 = base64.b64encode(html_contenu.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{titre}.html">📥 Télécharger le dossier complet</a>'
    st.markdown(href, unsafe_allow_html=True)

# ---------------------------------------------------------
# AUTHENTIFICATION
# ---------------------------------------------------------
if not is_connecte():
    login()
    st.stop()

# ---------------------------------------------------------
# STYLE GLOBAL (CSS)
# ---------------------------------------------------------
st.markdown("""
<style>
body { font-family: 'Segoe UI', sans-serif; }
table { width: 100%; border-collapse: collapse; }
th, td { border: 1px solid #ddd; padding: 8px; }
th { background-color: #1f77b4; color: white; font-weight: bold; }
tr:nth-child(even) { background-color: #f9f9f9; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# MENU LATÉRAL
# ---------------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/96/accounting.png", width=80)
st.sidebar.title("Superviseur IA Comptable")
st.sidebar.markdown(f"👤 Connecté : **{st.session_state['username']}**")
st.sidebar.markdown("---")
logout()

# --- MODIFICATION ICI : AJOUT DE BENFORD DANS LA LISTE ---
page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Accueil",
        "📁 Dossiers Clients",
        "🧾 OCR Facture",
        "📊 Analyse Balance",
        "📂 Traitement FEC",
        "🛡️ Benford (Audit de fraude)",
        "💳 Traitement Factures",
        "🏦 Rapprochement Bancaire",
        "🔗 Cohérence Inter-Documents",
        "🚨 Alertes de Gestion",
        "📰 Veille Fiscale",
        "📋 Analyse Bilan",
        "📈 Compte de Résultat"
    ]
)

# ---------------------------------------------------------
# PAGE : ACCUEIL
# ---------------------------------------------------------
if page == "🏠 Accueil":
    import plotly.express as px

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
    col7, col8 = st.columns(2)
    col7.warning("📋 Analyse Bilan\nRatios financiers et structure")
    col8.warning("📈 Compte de Résultat\nSIG, marges et rentabilité")

    st.markdown("---")
    st.warning("📰 Veille Fiscale — Restez à jour sur la réglementation française")

# ... [Les autres pages restent identiques jusqu'au bloc Traitement FEC] ...

# ---------------------------------------------------------
# PAGE : TRAITEMENT FEC
# ---------------------------------------------------------
elif page == "📂 Traitement FEC":
    st.title("📂 Traitement FEC")

    clients = lister_clients()
    client_id = None
    exercice = ""
    if clients:
        st.subheader("📁 Associer à un dossier client (optionnel)")
        options = {"-- Aucun --": None}
        options.update({f"{c[1]}": c[0] for c in clients})
        choix = st.selectbox("Client", list(options.keys()), key="fec_client")
        client_id = options[choix]
        exercice = st.text_input("Exercice (ex: 2024)", key="fec_exercice")

    fichier = st.file_uploader("Importer un fichier FEC", type=["txt"])
    if fichier:
        st.info("Traitement en cours…")
        resultat = traiter_fec(fichier)
        st.subheader("Résultat de l'analyse FEC :")
        st.markdown(resultat)
        
        telecharger_analyse("Analyse_FEC", resultat)
        telecharger_word("Analyse_FEC", resultat, exercice=exercice)

        if client_id:
            if st.button("💾 Sauvegarder dans le dossier client"):
                sauvegarder_analyse(client_id, "📂 FEC", fichier.name, resultat, exercice)
                st.success("✅ Analyse sauvegardée !")

# ---------------------------------------------------------
# NOUVELLE PAGE : BENFORD (AUDIT DE FRAUDE)
# ---------------------------------------------------------
elif page == "🛡️ Benford (Audit de fraude)":
    st.title("🛡️ Audit de Supervision Avancé (Loi de Benford)")
    st.markdown("Cette analyse statistique permet de détecter des anomalies potentielles ou des manipulations dans les montants comptables.")

    fichier_benford = st.file_uploader("Importer un fichier FEC (txt) ou Excel pour audit", type=["txt", "xlsx", "csv"])
    
    if fichier_benford:
        try:
            if fichier_benford.name.endswith(".txt"):
                df_audit = pd.read_csv(fichier_benford, sep="\t", dtype=str)
            elif fichier_benford.name.endswith(".csv"):
                df_audit = pd.read_csv(fichier_benford, dtype=str)
            else:
                df_audit = pd.read_excel(fichier_benford, dtype=str)

            st.write("Aperçu des données :")
            st.dataframe(df_audit.head(5))

            # Détection automatique de la colonne montant
            col_montant = None
            colonnes_possibles = ['Debit', 'Montant', 'Montant_HT', 'Debit_Montant', 'DEBIT', 'MONTANT']
            for c in colonnes_possibles:
                if c in df_audit.columns:
                    col_montant = c
                    break
            
            if not col_montant:
                col_montant = st.selectbox("Sélectionnez la colonne des montants :", df_audit.columns)

            if st.button("Lancer l'audit statistique"):
                fig, rapp, risque = analyse_benford_complete(df_audit, col_montant=col_montant)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown(rapp)
                    if risque == "Élevé":
                        st.error("🚨 Alerte : La distribution des montants est suspecte. Risque de manipulation élevé.")
                    elif risque == "Modéré":
                        st.warning("⚠️ Attention : Des écarts sont visibles. À vérifier.")
                    else:
                        st.success("✅ Cohérence statistique validée.")
                else:
                    st.warning(rapp)

        except Exception as e:
            st.error(f"Erreur lors de l'audit : {e}")

# ... [Le reste du code pour les autres pages continue ici] ...
# (Rapprochement Bancaire, Cohérence, etc. tels que dans votre original)
