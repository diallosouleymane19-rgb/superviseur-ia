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

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Accueil",
        "📁 Dossiers Clients",
        "🧾 OCR Facture",
        "📊 Analyse Balance",
        "📂 Traitement FEC",
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

    st.markdown("---")
    st.subheader("📊 Tableau de Bord")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Répartition des charges (exemple)**")
        df_charges = pd.DataFrame({
            "Poste": ["Achats", "Salaires", "Loyer", "Impôts", "Autres"],
            "Montant": [45000, 120000, 18000, 12000, 8000]
        })
        fig1 = px.pie(df_charges, values="Montant", names="Poste",
                      color_discrete_sequence=px.colors.sequential.Blues_r)
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.markdown("**Évolution du chiffre d'affaires (exemple)**")
        df_ca = pd.DataFrame({
            "Mois": ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun",
                     "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"],
            "CA": [32000, 35000, 41000, 38000, 45000, 52000,
                   48000, 43000, 55000, 61000, 58000, 70000]
        })
        fig2 = px.bar(df_ca, x="Mois", y="CA", color="CA",
                      color_continuous_scale="Blues")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("**Comparaison Charges vs Produits par trimestre (exemple)**")
    df_cp = pd.DataFrame({
        "Trimestre": ["T1", "T2", "T3", "T4"],
        "Charges": [108000, 103000, 110000, 136000],
        "Produits": [108000, 135000, 146000, 189000]
    })
    fig3 = px.line(df_cp, x="Trimestre", y=["Charges", "Produits"],
                   markers=True, color_discrete_sequence=["#ef553b", "#00cc96"])
    st.plotly_chart(fig3, use_container_width=True)

# ---------------------------------------------------------
# PAGE : DOSSIERS CLIENTS
# ---------------------------------------------------------
elif page == "📁 Dossiers Clients":
    st.title("📁 Gestion des Dossiers Clients")
    st.markdown("---")

    onglet1, onglet2, onglet3 = st.tabs(["➕ Nouveau Client", "📋 Liste des Clients", "📊 Dossier Client"])

    with onglet1:
        st.subheader("➕ Créer un nouveau dossier client")
        nom = st.text_input("Nom du client *")
        col1, col2 = st.columns(2)
        with col1:
            siret = st.text_input("SIRET")
            contact = st.text_input("Contact")
        with col2:
            secteur = st.text_input("Secteur d'activité")
            email = st.text_input("Email")

        if st.button("Créer le dossier"):
            if nom:
                creer_client(nom, siret, secteur, contact, email)
                st.success(f"✅ Dossier **{nom}** créé avec succès !")
                st.rerun()
            else:
                st.warning("Le nom du client est obligatoire.")

    with onglet2:
        st.subheader("📋 Liste des dossiers clients")
        clients = lister_clients()

        if not clients:
            st.info("Aucun dossier client créé.")
        else:
            for client in clients:
                client_id, nom, siret, secteur, contact, email, date_creation = client
                analyses = lister_analyses(client_id)

                with st.expander(f"📁 {nom} — {len(analyses)} analyse(s)"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**SIRET :** {siret or 'Non renseigné'}")
                        st.write(f"**Secteur :** {secteur or 'Non renseigné'}")
                    with col2:
                        st.write(f"**Contact :** {contact or 'Non renseigné'}")
                        st.write(f"**Email :** {email or 'Non renseigné'}")
                    st.write(f"**Créé le :** {date_creation}")

                    col1, col2 = st.columns(2)
                    with col2:
                        if st.button(f"🗑️ Supprimer", key=f"del_{client_id}"):
                            supprimer_client(client_id)
                            st.success(f"Dossier {nom} supprimé.")
                            st.rerun()

    with onglet3:
        st.subheader("📊 Dossier Client")
        clients = lister_clients()

        if not clients:
            st.info("Aucun client disponible.")
        else:
            options = {f"{c[1]}": c[0] for c in clients}
            choix = st.selectbox("Sélectionner un client", list(options.keys()))
            client_id = options[choix]
            client_nom = choix

            analyses = lister_analyses(client_id)
            st.markdown(f"### 📁 {client_nom} — {len(analyses)} analyse(s)")

            if not analyses:
                st.info("Aucune analyse enregistrée pour ce client.")
            else:
                for analyse in analyses:
                    analyse_id, type_analyse, titre, date_analyse, exercice = analyse
                    with st.expander(f"{type_analyse} — {titre} ({date_analyse})"):
                        detail = get_analyse(analyse_id)
                        if detail:
                            st.markdown(detail[4])
                            telecharger_word(f"{type_analyse}_{client_nom}", detail[4], client_nom, exercice)
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("🗑️ Supprimer", key=f"delA_{analyse_id}"):
                                supprimer_analyse(analyse_id)
                                st.rerun()

            st.markdown("---")
            if st.button("📥 Télécharger le dossier complet"):
                rapport = generer_rapport_client(client_id)
                telecharger_rapport_html(f"Dossier_{client_nom}", rapport)

# ---------------------------------------------------------
# PAGE : OCR FACTURE
# ---------------------------------------------------------
elif page == "🧾 OCR Facture":
    st.title("🧾 OCR Facture (IA Vision)")

    clients = lister_clients()
    client_id = None
    exercice = ""
    if clients:
        st.subheader("📁 Associer à un dossier client (optionnel)")
        options = {"-- Aucun --": None}
        options.update({f"{c[1]}": c[0] for c in clients})
        choix = st.selectbox("Client", list(options.keys()), key="ocr_client")
        client_id = options[choix]
        exercice = st.text_input("Exercice (ex: 2024)", key="ocr_exercice")

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
Extrais et structure : Fournisseur, Client, Numéro facture, Date, Montant HT, TVA, TTC, Mode paiement, Compte comptable, Observations.
        """
        analyse = appel_mistral(prompt)
        st.markdown(analyse)
        telecharger_analyse("Analyse_Facture", analyse)
        telecharger_word("Analyse_Facture", analyse, exercice=exercice)

        if client_id:
            if st.button("💾 Sauvegarder dans le dossier client"):
                sauvegarder_analyse(client_id, "🧾 OCR Facture", fichier.name, analyse, exercice)
                st.success("✅ Analyse sauvegardée !")

# ---------------------------------------------------------
# PAGE : ANALYSE BALANCE
# ---------------------------------------------------------
elif page == "📊 Analyse Balance":
    st.title("📊 Analyse de la Balance Comptable")

    clients = lister_clients()
    client_id = None
    exercice = ""
    if clients:
        st.subheader("📁 Associer à un dossier client (optionnel)")
        options = {"-- Aucun --": None}
        options.update({f"{c[1]}": c[0] for c in clients})
        choix = st.selectbox("Client", list(options.keys()), key="balance_client")
        client_id = options[choix]
        exercice = st.text_input("Exercice (ex: 2024)", key="balance_exercice")

    fichier = st.file_uploader("Importer une balance (Excel ou CSV)", type=["xlsx", "csv"])
    if fichier:
        try:
            df = pd.read_csv(fichier) if fichier.name.endswith(".csv") else pd.read_excel(fichier)
            st.subheader("Aperçu de la balance :")
            st.dataframe(df)
            if st.button("Analyser la balance"):
                st.info("Analyse IA en cours…")
                resultat = analyse_balance_ai(df)
                st.subheader("Analyse IA :")
                st.markdown(resultat)
                telecharger_analyse("Analyse_Balance", resultat)
                telecharger_word("Analyse_Balance", resultat, exercice=exercice)

                if client_id:
                    if st.button("💾 Sauvegarder dans le dossier client"):
                        sauvegarder_analyse(client_id, "📊 Balance", fichier.name, resultat, exercice)
                        st.success("✅ Analyse sauvegardée !")
        except Exception as e:
            st.error(f"Erreur : {e}")

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
        # --- BLOC ORIGINAL : TRAITEMENT FEC ---
        st.info("Traitement en cours…")
        resultat = traiter_fec(fichier)
        st.subheader("Résultat de l'analyse FEC :")
        st.markdown(resultat)
        
        # --- NOUVELLE BRIQUE : AUDIT BENFORD ---
        st.markdown("---")
        st.subheader("🛡️ Audit de Supervision Avancé (Loi de Benford)")
        if st.button("Lancer l'audit de fraude statistique"):
            try:
                # On recharge le FEC en DataFrame pour l'analyse statistique
                # On suppose le séparateur tabulation classique du FEC
                df_fec = pd.read_csv(fichier, sep="\t", dtype=str)
                
                # Détection automatique de la colonne montant
                col_montant = None
                for c in ['Debit', 'Montant', 'Montant_HT', 'Debit_Montant']:
                    if c in df_fec.columns:
                        col_montant = c
                        break
                
                if col_montant:
                    fig, rapp, risque = analyse_benford_complete(df_fec, col_montant=col_montant)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                        st.markdown(rapp)
                        if risque == "Élevé":
                            st.error("🚨 Alerte : La distribution des montants est suspecte. Risque de manipulation élevé.")
                    else:
                        st.warning(rapp)
                else:
                    st.error("Impossible de trouver une colonne 'Debit' ou 'Montant' pour l'audit statistique.")
            except Exception as e:
                st.error(f"Erreur lors de l'audit statistique : {e}")

        # --- EXPORTS ET SAUVEGARDE ---
        st.markdown("---")
        telecharger_analyse("Analyse_FEC", resultat)
        telecharger_word("Analyse_FEC", resultat, exercice=exercice)

        if client_id:
            if st.button("💾 Sauvegarder dans le dossier client"):
                sauvegarder_analyse(client_id, "📂 FEC", fichier.name, resultat, exercice)
                st.success("✅ Analyse sauvegardée !")

# ---------------------------------------------------------
# PAGE : TRAITEMENT FACTURES
# ---------------------------------------------------------
elif page == "💳 Traitement Factures":
    st.title("💳 Traitement Factures Excel / CSV")

    clients = lister_clients()
    client_id = None
    exercice = ""
    if clients:
        st.subheader("📁 Associer à un dossier client (optionnel)")
        options = {"-- Aucun --": None}
        options.update({f"{c[1]}": c[0] for c in clients})
        choix = st.selectbox("Client", list(options.keys()), key="fact_client")
        client_id = options[choix]
        exercice = st.text_input("Exercice (ex: 2024)", key="fact_exercice")

    fichier = st.file_uploader("Importer un fichier de factures", type=["xlsx", "csv"])
    if fichier:
        try:
            df = pd.read_csv(fichier) if fichier.name.endswith(".csv") else pd.read_excel(fichier)
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
                prompt = f"Tu es expert-comptable. Analyse ces factures :\n{apercu}\n1. RÉSUMÉ 2. ANOMALIES 3. PÉRIODE 4. RAPPROCHEMENT 5. RECOMMANDATIONS"
                analyse = appel_mistral(prompt)
                st.subheader("Analyse IA :")
                st.markdown(analyse)
                telecharger_analyse("Analyse_Factures", analyse)
                telecharger_word("Analyse_Factures", analyse, exercice=exercice)

                if client_id:
                    if st.button("💾 Sauvegarder dans le dossier client"):
                        sauvegarder_analyse(client_id, "💳 Factures", fichier.name, analyse, exercice)
                        st.success("✅ Analyse sauvegardée !")
        except Exception as e:
            st.error(f"Erreur : {e}")

# ---------------------------------------------------------
# PAGE : RAPPROCHEMENT BANCAIRE
# ---------------------------------------------------------
elif page == "🏦 Rapprochement Bancaire":
    st.title("🏦 Rapprochement Bancaire")

    clients = lister_clients()
    client_id = None
    exercice = ""
    if clients:
        st.subheader("📁 Associer à un dossier client (optionnel)")
        options = {"-- Aucun --": None}
        options.update({f"{c[1]}": c[0] for c in clients})
        choix = st.selectbox("Client", list(options.keys()), key="rappr_client")
        client_id = options[choix]
        exercice = st.text_input("Exercice (ex: 2024)", key="rappr_exercice")

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
            st.dataframe(df_banque)
            st.dataframe(df_compta)
            if st.button("Lancer le rapprochement"):
                st.info("Rapprochement en cours…")
                resultat = rapprocher_banque_compta(df_banque, df_compta)
                st.markdown(resultat)
                telecharger_analyse("Rapprochement_Bancaire", resultat)
                telecharger_word("Rapprochement_Bancaire", resultat, exercice=exercice)

                if client_id:
                    if st.button("💾 Sauvegarder dans le dossier client"):
                        sauvegarder_analyse(client_id, "🏦 Rapprochement", "Rapprochement bancaire", resultat, exercice)
                        st.success("✅ Analyse sauvegardée !")
        except Exception as e:
            st.error(f"Erreur : {e}")

# ---------------------------------------------------------
# PAGE : COHÉRENCE INTER-DOCUMENTS
# ---------------------------------------------------------
elif page == "🔗 Cohérence Inter-Documents":
    st.title("🔗 Cohérence Inter-Documents")

    clients = lister_clients()
    client_id = None
    exercice = ""
    if clients:
        options = {"-- Aucun --": None}
        options.update({f"{c[1]}": c[0] for c in clients})
        choix = st.selectbox("Client", list(options.keys()), key="coh_client")
        client_id = options[choix]
        exercice = st.text_input("Exercice", key="coh_exercice")

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
            st.markdown(resultat)
            telecharger_analyse("Coherence_Inter_Documents", resultat)
            telecharger_word("Coherence_Inter_Documents", resultat, exercice=exercice)

            if client_id:
                if st.button("💾 Sauvegarder dans le dossier client"):
                    sauvegarder_analyse(client_id, "🔗 Cohérence", "Cohérence inter-documents", resultat, exercice)
                    st.success("✅ Analyse sauvegardée !")

# ---------------------------------------------------------
# PAGE : ALERTES DE GESTION
# ---------------------------------------------------------
elif page == "🚨 Alertes de Gestion":
    st.title("🚨 Alertes de Gestion")

    clients = lister_clients()
    client_id = None
    exercice = ""
    if clients:
        options = {"-- Aucun --": None}
        options.update({f"{c[1]}": c[0] for c in clients})
        choix = st.selectbox("Client", list(options.keys()), key="alert_client")
        client_id = options[choix]
        exercice = st.text_input("Exercice", key="alert_exercice")

    fichier = st.file_uploader("Importer un fichier financier", type=["xlsx", "csv"])
    if fichier:
        try:
            df = pd.read_csv(fichier) if fichier.name.endswith(".csv") else pd.read_excel(fichier)
            st.dataframe(df)
            if st.button("Générer les alertes"):
                st.info("Analyse en cours…")
                resultat = analyser_alertes(df)
                st.markdown(resultat)
                telecharger_analyse("Alertes_Gestion", resultat)
                telecharger_word("Alertes_Gestion", resultat, exercice=exercice)

                if client_id:
                    if st.button("💾 Sauvegarder dans le dossier client"):
                        sauvegarder_analyse(client_id, "🚨 Alertes", fichier.name, resultat, exercice)
                        st.success("✅ Analyse sauvegardée !")
        except Exception as e:
            st.error(f"Erreur : {e}")

# ---------------------------------------------------------
# PAGE : VEILLE FISCALE
# ---------------------------------------------------------
elif page == "📰 Veille Fiscale":
    st.title("📰 Veille Fiscale")
    if st.button("Obtenir la veille fiscale"):
        st.info("Génération en cours…")
        resultat = obtenir_veille_fiscale()
        st.markdown(resultat, unsafe_allow_html=True)
        telecharger_analyse("Veille_Fiscale", resultat)
        telecharger_word("Veille_Fiscale", resultat)

# ---------------------------------------------------------
# PAGE : ANALYSE BILAN
# ---------------------------------------------------------
elif page == "📋 Analyse Bilan":
    st.title("📋 Analyse du Bilan Comptable")

    clients = lister_clients()
    client_id = None
    exercice = ""
    if clients:
        st.subheader("📁 Associer à un dossier client (optionnel)")
        options = {"-- Aucun --": None}
        options.update({f"{c[1]}": c[0] for c in clients})
        choix = st.selectbox("Client", list(options.keys()), key="bilan_client")
        client_id = options[choix]
        exercice = st.text_input("Exercice (ex: 2024)", key="bilan_exercice")

    fichier = st.file_uploader("Importer un bilan (Excel, CSV ou PDF)", type=["xlsx", "csv", "pdf", "png", "jpg", "jpeg"])
    if fichier:
        try:
            if fichier.name.endswith(".csv"):
                df = pd.read_csv(fichier)
                st.dataframe(df)
                donnees = df.head(50).to_string()
            elif fichier.name.endswith(".xlsx"):
                df = pd.read_excel(fichier)
                st.dataframe(df)
                donnees = df.head(50).to_string()
            else:
                st.info("Extraction du texte en cours…")
                donnees = ocr_image_mistral(fichier)
                st.text_area("Texte extrait :", donnees, height=200)

            if st.button("Analyser le bilan"):
                st.info("Analyse IA en cours…")
                resultat = analyser_bilan_texte(donnees)
                st.subheader("Analyse IA :")
                st.markdown(resultat)
                telecharger_analyse("Analyse_Bilan", resultat)
                telecharger_word("Analyse_Bilan", resultat, exercice=exercice)

                if client_id:
                    if st.button("💾 Sauvegarder dans le dossier client"):
                        sauvegarder_analyse(client_id, "📋 Bilan", fichier.name, resultat, exercice)
                        st.success("✅ Analyse sauvegardée !")
        except Exception as e:
            st.error(f"Erreur : {e}")

# ---------------------------------------------------------
# PAGE : COMPTE DE RÉSULTAT
# ---------------------------------------------------------
elif page == "📈 Compte de Résultat":
    st.title("📈 Analyse du Compte de Résultat")

    clients = lister_clients()
    client_id = None
    exercice = ""
    if clients:
        st.subheader("📁 Associer à un dossier client (optionnel)")
        options = {"-- Aucun --": None}
        options.update({f"{c[1]}": c[0] for c in clients})
        choix = st.selectbox("Client", list(options.keys()), key="cr_client")
        client_id = options[choix]
        exercice = st.text_input("Exercice (ex: 2024)", key="cr_exercice")

    fichier = st.file_uploader("Importer un compte de résultat (Excel, CSV ou PDF)", type=["xlsx", "csv", "pdf", "png", "jpg", "jpeg"])
    if fichier:
        try:
            if fichier.name.endswith(".csv"):
                df = pd.read_csv(fichier)
                st.dataframe(df)
                donnees = df.head(50).to_string()
            elif fichier.name.endswith(".xlsx"):
                df = pd.read_excel(fichier)
                st.dataframe(df)
                donnees = df.head(50).to_string()
            else:
                st.info("Extraction du texte en cours…")
                donnees = ocr_image_mistral(fichier)
                st.text_area("Texte extrait :", donnees, height=200)

            if st.button("Analyser le compte de résultat"):
                st.info("Analyse IA en cours…")
                resultat = analyser_cr_texte(donnees)
                st.subheader("Analyse IA :")
                st.markdown(resultat)
                telecharger_analyse("Analyse_Compte_Resultat", resultat)
                telecharger_word("Analyse_Compte_Resultat", resultat, exercice=exercice)

                if client_id:
                    if st.button("💾 Sauvegarder dans le dossier client"):
                        sauvegarder_analyse(client_id, "📈 Compte de Résultat", fichier.name, resultat, exercice)
                        st.success("✅ Analyse sauvegardée !")
        except Exception as e:
            st.error(f"Erreur : {e}")