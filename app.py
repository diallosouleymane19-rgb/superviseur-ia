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

# --- IMPORT MODULE BENFORD ---
from benford_module import analyse_benford_complete

# Initialiser la base de données
init_db()

# ---------------------------------------------------------
# FONCTIONS EXPORT
# ---------------------------------------------------------
def telecharger_analyse(titre, contenu):
    html = f"<html><body style='font-family:sans-serif;'><h1>{titre}</h1><pre>{contenu}</pre></body></html>"
    b64 = base64.b64encode(html.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{titre}.html">📥 Télécharger en HTML</a>'
    st.markdown(href, unsafe_allow_html=True)

def telecharger_word(titre, contenu, nom_client="", exercice=""):
    buffer = export_analyse_word(titre, contenu, nom_client, exercice)
    st.download_button(label="📄 Télécharger en Word", data=buffer, file_name=f"{titre}.docx")

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
# MENU LATÉRAL
# ---------------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/96/accounting.png", width=80)
st.sidebar.title("Superviseur IA")
st.sidebar.markdown(f"👤 **{st.session_state['username']}**")
logout()

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Accueil", "📁 Dossiers Clients", "🧾 OCR Facture", "📊 Analyse Balance", 
        "📂 Traitement FEC", "🛡️ Benford (Audit de fraude)", "💳 Traitement Factures", 
        "🏦 Rapprochement Bancaire", "🔗 Cohérence Inter-Documents", "🚨 Alertes de Gestion", 
        "📰 Veille Fiscale", "📋 Analyse Bilan", "📈 Compte de Résultat"
    ]
)

# ---------------------------------------------------------
# PAGE : ACCUEIL
# ---------------------------------------------------------
if page == "🏠 Accueil":
    import plotly.express as px
    st.title("🏠 Superviseur IA Comptable")
    st.markdown("### Bienvenue dans votre assistant intelligent")
    col1, col2 = st.columns(2)
    with col1:
        st.info("Utilisez le menu à gauche pour naviguer dans les modules d'analyse.")
    with col2:
        st.success("Toutes les analyses peuvent être exportées en Word (Format SMD Consulting).")

# ---------------------------------------------------------
# PAGE : DOSSIERS CLIENTS
# ---------------------------------------------------------
elif page == "📁 Dossiers Clients":
    st.title("📁 Gestion des Dossiers Clients")
    onglet1, onglet2 = st.tabs(["➕ Nouveau Client", "📋 Liste & Dossiers"])
    with onglet1:
        nom = st.text_input("Nom du client")
        if st.button("Créer le dossier"):
            if nom: 
                creer_client(nom, "", "", "", "")
                st.success("Client créé")
    with onglet2:
        clients = lister_clients()
        for c in clients:
            with st.expander(f"Dossier {c[1]}"):
                st.write(f"ID: {c[0]}")
                if st.button(f"Supprimer {c[1]}", key=f"del_{c[0]}"):
                    supprimer_client(c[0])
                    st.rerun()

# ---------------------------------------------------------
# PAGE : OCR FACTURE
# ---------------------------------------------------------
elif page == "🧾 OCR Facture":
    st.title("🧾 OCR Facture (IA Vision)")
    fichier = st.file_uploader("Facture (PDF/Image)", type=["pdf", "png", "jpg"])
    if fichier:
        texte = ocr_image_mistral(fichier)
        st.subheader("Analyse :")
        analyse = appel_mistral(f"Analyse cette facture : {texte}")
        st.markdown(analyse)
        telecharger_word("Analyse_Facture", analyse)

# ---------------------------------------------------------
# PAGE : ANALYSE BALANCE
# ---------------------------------------------------------
elif page == "📊 Analyse Balance":
    st.title("📊 Analyse de la Balance")
    fichier = st.file_uploader("Balance (Excel/CSV)", type=["xlsx", "csv"])
    if fichier:
        df = pd.read_excel(fichier) if fichier.name.endswith('xlsx') else pd.read_csv(fichier)
        if st.button("Lancer l'analyse IA"):
            resultat = analyse_balance_ai(df)
            st.markdown(resultat)
            telecharger_word("Analyse_Balance", resultat)

# ---------------------------------------------------------
# PAGE : TRAITEMENT FEC
# ---------------------------------------------------------
elif page == "📂 Traitement FEC":
    st.title("📂 Traitement FEC")
    fichier = st.file_uploader("Fichier FEC (.txt)", type=["txt"])
    if fichier:
        resultat = traiter_fec(fichier)
        st.markdown(resultat)
        telecharger_word("Analyse_FEC", resultat)
        
# ---------------------------------------------------------
# PAGE : TRAITEMENT FACTURES (LOTS)
# ---------------------------------------------------------
elif page == "💳 Traitement Factures":
    st.title("💳 Traitement des Factures (Analyse de Lot)")
    st.markdown("Déposez plusieurs factures pour une analyse groupée des montants et de la TVA.")
    
    fichiers = st.file_uploader("Importer des factures", type=["pdf", "png", "jpg"], accept_multiple_files=True)
    
    if fichiers:
        resultats = []
        for f in fichiers:
            with st.spinner(f"Analyse de {f.name}..."):
                texte_brut = ocr_image_mistral(f)
                prompt = f"Extrais les informations suivantes : Date, Fournisseur, HT, TVA, TTC de ce texte : {texte_brut}"
                analyse = extraire_contenu_mistral(prompt)
                resultats.append({"Fichier": f.name, "Détails": analyse})
        
        # Affichage des résultats
        for res in resultats:
            with st.expander(f"Résultat : {res['Fichier']}"):
                st.markdown(res['Détails'])
        
        # Bouton d'export global
        texte_complet = "\n\n".join([f"--- {r['Fichier']} ---\n{r['Détails']}" for r in resultats])
        telecharger_word("Analyse_Lots_Factures", texte_complet)

# ---------------------------------------------------------
# PAGE : BENFORD (NOUVEAU)
# ---------------------------------------------------------
elif page == "🛡️ Benford (Audit de fraude)":
    st.title("🛡️ Audit de fraude (Loi de Benford)")
    fichier = st.file_uploader("Fichier pour audit (FEC ou Excel)", type=["txt", "xlsx", "csv"])
    if fichier:
        df = pd.read_csv(fichier, sep="\t") if fichier.name.endswith(".txt") else pd.read_excel(fichier)
        col_montant = st.selectbox("Colonne des montants", df.columns)
        if st.button("Lancer l'audit"):
            fig, rapp, risque = analyse_benford_complete(df, col_montant=col_montant)
            st.plotly_chart(fig)
            st.markdown(rapp)

# ---------------------------------------------------------
# PAGE : RAPPROCHEMENT BANCAIRE
# ---------------------------------------------------------
elif page == "🏦 Rapprochement Bancaire":
    st.title("🏦 Rapprochement Bancaire")
    f1 = st.file_uploader("Relevé Bancaire", type=["xlsx", "csv"])
    f2 = st.file_uploader("Compta", type=["xlsx", "csv"])
    if f1 and f2:
        if st.button("Comparer"):
            df1 = pd.read_excel(f1)
            df2 = pd.read_excel(f2)
            res = rapprocher_banque_compta(df1, df2)
            st.markdown(res)

# ---------------------------------------------------------
# PAGE : COHÉRENCE
# ---------------------------------------------------------
elif page == "🔗 Cohérence Inter-Documents":
    st.title("🔗 Cohérence Inter-Documents")
    f_fact = st.file_uploader("Import Factures", type=["xlsx"])
    f_bal = st.file_uploader("Import Balance", type=["xlsx"])
    if st.button("Analyser la cohérence"):
        res = analyser_coherence(pd.read_excel(f_fact) if f_fact else None, pd.read_excel(f_bal) if f_bal else None, None)
        st.markdown(res)

# ---------------------------------------------------------
# PAGE : ALERTES
# ---------------------------------------------------------
elif page == "🚨 Alertes de Gestion":
    st.title("🚨 Alertes de Gestion")
    f = st.file_uploader("Fichier financier", type=["xlsx"])
    if f:
        res = analyser_alertes(pd.read_excel(f))
        st.markdown(res)

# ---------------------------------------------------------
# PAGE : VEILLE FISCALE
# ---------------------------------------------------------
elif page == "📰 Veille Fiscale":
    st.title("📰 Veille Fiscale")
    if st.button("Actualiser la veille"):
        res = obtenir_veille_fiscale()
        st.markdown(res, unsafe_allow_html=True)

# ---------------------------------------------------------
# PAGE : BILAN / CR
# ---------------------------------------------------------
elif page == "📋 Analyse Bilan":
    st.title("📋 Analyse du Bilan")
    f = st.file_uploader("Bilan (PDF/Excel)", type=["pdf", "xlsx"])
    if f:
        res = analyser_bilan_texte(ocr_image_mistral(f) if f.name.endswith(".pdf") else "Données Excel")
        st.markdown(res)

elif page == "📈 Compte de Résultat":
    st.title("📈 Compte de Résultat")
    f = st.file_uploader("CR (PDF/Excel)", type=["pdf", "xlsx"])
    if f:
        res = analyser_cr_texte(ocr_image_mistral(f) if f.name.endswith(".pdf") else "Données Excel")
        st.markdown(res)
