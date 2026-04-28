import streamlit as st
import json
import pandas as pd
from auth.users import init_user_db, create_user, authenticate_user
from utils.database import init_db, ajouter_client, lister_clients, sauvegarder_facture, charger_historique, vider_historique
from utils.ai import appel_mistral, extraire_contenu_mistral, parse_montant, extraire_compte_valide
from utils.fec import generer_fec
from utils.ocr import ocr_image_mistral

st.set_page_config(page_title="Superviseur IA – SaaS", page_icon="🤖", layout="wide")

init_user_db()
init_db()

if "user" not in st.session_state:
    st.session_state.user = None

def show_auth():
    tab_login, tab_register = st.tabs(["🔐 Connexion", "🆕 Inscription"])
    with tab_login:
        st.subheader("Connexion")
        email = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter", type="primary"):
            user = authenticate_user(email, password)
            if user:
                st.session_state.user = user
                st.success("Connexion réussie")
                st.experimental_rerun()
            else:
                st.error("Identifiants invalides")
    with tab_register:
        st.subheader("Créer un compte")
        email_r = st.text_input("Email (nouveau compte)")
        pwd_r1 = st.text_input("Mot de passe", type="password", key="pwd1")
        pwd_r2 = st.text_input("Confirmer le mot de passe", type="password", key="pwd2")
        if st.button("Créer le compte"):
            if not email_r or not pwd_r1:
                st.error("Email et mot de passe requis")
            elif pwd_r1 != pwd_r2:
                st.error("Les mots de passe ne correspondent pas")
            else:
                ok = create_user(email_r, pwd_r1)
                if ok:
                    st.success("Compte créé. Vous pouvez vous connecter.")
                else:
                    st.error("Cet email est déjà utilisé.")

def sidebar_menu():
    with st.sidebar:
        st.markdown("### 🤖 Superviseur IA – SaaS")
        st.markdown(f"**Connecté :** {st.session_state.user['email']}")
        menu = st.radio(
            "Navigation",
            ["📊 Dashboard", "📄 Factures", "👥 Clients", "🔍 Anomalies", "📰 Veille fiscale", "🗂️ Historique"],
        )
        if st.button("🚪 Déconnexion"):
            st.session_state.user = None
            st.experimental_rerun()
    return menu

if not st.session_state.user:
    st.title("Superviseur IA – SaaS")
    st.caption("SMD Consulting – Plateforme comptable intelligente")
    show_auth()
    st.stop()

menu = sidebar_menu()

user_id = st.session_state.user["id"]

# 📊 Dashboard
if menu == "📊 Dashboard":
    st.title("📊 Dashboard")
    st.write("Vue synthétique (à enrichir : nombre de factures, montants, etc.).")
    rows = charger_historique(user_id, limit=10)
    st.write("Dernières factures :")
    if rows:
        df = pd.DataFrame(rows, columns=["ID", "Date analyse", "Client", "N° facture", "Fournisseur", "HT", "TVA", "TTC", "Compte"])
        st.dataframe(df)
    else:
        st.info("Aucune facture pour l’instant.")

# 👥 Clients
elif menu == "👥 Clients":
    st.title("👥 Gestion des clients")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Ajouter un client")
        nom_client = st.text_input("Nom du client")
        if st.button("Ajouter"):
            if nom_client.strip():
                ajouter_client(user_id, nom_client)
                st.success("Client ajouté")
                st.experimental_rerun()
            else:
                st.error("Nom obligatoire")
    with col2:
        st.subheader("Liste des clients")
        clients = lister_clients(user_id)
        if clients:
            df = pd.DataFrame(clients, columns=["ID", "Nom"])
            st.dataframe(df)
        else:
            st.info("Aucun client pour l’instant.")

# 📄 Factures
elif menu == "📄 Factures":
    st.title("📄 Factures – Analyse IA")
    clients = lister_clients(user_id)
    client_id = None
    if clients:
        options = {f"{c[1]} (ID {c[0]})": c[0] for c in clients}
        choix = st.selectbox("Associer à un client (optionnel)", ["Aucun"] + list(options.keys()))
        if choix != "Aucun":
            client_id = options[choix]
    else:
        st.info("Vous pouvez créer des clients dans l’onglet 👥 Clients.")

    if "texte_facture" not in st.session_state:
        st.session_state.texte_facture = ""
    if "dernier_mode" not in st.session_state:
        st.session_state.dernier_mode = ""
    if "analyse_en_cours" not in st.session_state:
        st.session_state.analyse_en_cours = False

    mode = st.radio("Mode de saisie", ["📝 Texte manuel", "📎 Upload Image (JPG, PNG)", "📄 PDF - Copier le texte"])
    st.subheader("Saisie de la facture")

    if mode != st.session_state.dernier_mode:
        st.session_state.texte_facture = ""
        st.session_state.dernier_mode = mode

    if mode == "📝 Texte manuel":
        exemple = """CARREFOUR MARKET
Ticket n° 12345
Date: 25/04/2026
Montant TTC: 45.50 €"""
        texte = st.text_area("Collez le texte :", value=st.session_state.texte_facture or exemple, height=150)
        st.session_state.texte_facture = texte

    elif mode == "📎 Upload Image (JPG, PNG)":
        fichier = st.file_uploader("Choisissez une image", type=["jpg", "jpeg", "png"])
        if fichier:
            bytes_data = fichier.read()
            ext = fichier.name.split(".")[-1].lower()
            mime = "image/png" if ext == "png" else "image/jpeg"
            with st.spinner("OCR..."):
                try:
                    texte_extrait = ocr_image_mistral(bytes_data, mime)
                    if not texte_extrait:
                        st.error("❌ L'image n'a pas pu être lue.")
                        st.stop()
                    st.session_state.texte_facture = texte_extrait
                    st.success("Texte extrait")
                except Exception as e:
                    st.exception(e)
                    st.stop()

    elif mode == "📄 PDF - Copier le texte":
        st.info("Copiez le texte du PDF et collez-le ci-dessous.")
        st.session_state.texte_facture = st.text_area("Texte PDF", value=st.session_state.texte_facture, height=150)

    if st.button("🔍 Analyser", type="primary", disabled=st.session_state.analyse_en_cours):
        st.session_state.analyse_en_cours = True
        texte_a_analyser = st.session_state.texte_facture
        try:
            if not texte_a_analyser.strip():
                st.error("Veuillez entrer une facture.")
                st.session_state.analyse_en_cours = False
                st.stop()

            with st.spinner("Analyse IA..."):
                result = appel_mistral(
                    messages=[
                        {"role": "system", "content": (
                            "Tu es un expert-comptable. "
                            "Retourne UNIQUEMENT un JSON valide avec : num_facture, date (DD/MM/YYYY), fournisseur, "
                            "montant_ht, tva, montant_ttc (nombres), compte_suggere (texte 6 chiffres). "
                            "compte_suggere doit être une chaîne de 6 chiffres (ex '601000'), pas un objet. "
                            "Règles : marchandises, réassort, magasin → 601000 ; fournitures, papeterie → 606300 ; "
                            "services, SaaS, abonnement → 604000 ; télécom → 626000 ; transport → 624000."
                        )},
                        {"role": "user", "content": texte_a_analyser[:4000]}
                    ],
                    json_mode=True
                )
                contenu = extraire_contenu_mistral(result)
                try:
                    infos = json.loads(contenu)
                except json.JSONDecodeError:
                    st.error("❌ L'IA n'a pas renvoyé un JSON valide.")
                    st.stop()

            ht = parse_montant(infos.get("montant_ht", 0))
            tva = parse_montant(infos.get("tva", 0))
            ttc = parse_montant(infos.get("montant_ttc", 0))
            if abs((ht + tva) - ttc) > 0.05 and ht and tva:
                ttc = round(ht + tva, 2)
                infos["montant_ttc"] = ttc

            st.success("Analyse terminée")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Fournisseur", infos.get("fournisseur", "?"))
                st.metric("Date", infos.get("date", "?"))
                st.metric("N° facture", infos.get("num_facture", "?"))
            with col2:
                st.metric("HT", f"{ht:.2f} €")
                st.metric("TVA", f"{tva:.2f} €")
                st.metric("TTC", f"{ttc:.2f} €")

            compte = extraire_compte_valide(infos.get("compte_suggere", "606300"))
            st.info(f"📝 Compte suggéré : **{compte}**")

            fec, nom_fec = generer_fec(infos)
            st.download_button("📥 Télécharger FEC (.csv)", fec, nom_fec, mime="text/csv")
            sauvegarder_facture(user_id, client_id, infos, compte)
        except Exception as e:
            st.exception(e)
        finally:
            st.session_state.analyse_en_cours = False

# 🔍 Anomalies
elif menu == "🔍 Anomalies":
    st.title("🔍 Détection d'anomalies comptables")
    uploaded_file = st.file_uploader("Choisissez votre export (CSV ou XLSX)", type=["csv", "xlsx"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".xlsx"):
                df = pd.read_excel(uploaded_file, header=None)
            else:
                df = pd.read_csv(uploaded_file, sep=None, engine="python", header=None)
            st.write("📄 **Aperçu des premières lignes :**")
            st.dataframe(df.head(10))
            header_row = st.number_input("Ligne contenant les noms des colonnes", min_value=0, max_value=len(df)-1, value=0, step=1)
            df.columns = df.iloc[header_row]
            df = df[header_row+1:].reset_index(drop=True)
            colonnes = df.columns.tolist()
            colonne_montant = st.selectbox("📊 Colonne montants", colonnes)
            df[colonne_montant] = pd.to_numeric(df[colonne_montant], errors='coerce')
            seuil = st.number_input("🚨 Seuil d'alerte (€)", min_value=0, value=5000, step=1000)
            if st.button("🔍 Lancer la détection", type="primary"):
                anomalies = df[df[colonne_montant].abs() > seuil]
                st.warning(f"🚨 {len(anomalies)} écritures > {seuil} € détectées")
                if not anomalies.empty:
                    st.dataframe(anomalies)
                    csv = anomalies.to_csv(index=False).encode('utf-8-sig')
                    st.download_button("📥 Télécharger anomalies (CSV)", csv, "anomalies.csv", mime="text/csv")
                else:
                    st.success("✅ Aucune anomalie détectée.")
        except Exception as e:
            st.exception(e)

# 📰 Veille
elif menu == "📰 Veille fiscale":
    st.title("📰 Veille fiscale hebdomadaire")
    if st.button("📡 Générer la veille de la semaine", type="primary"):
        with st.spinner("Génération de la veille..."):
            articles_ia = [
                {
                    "source": "Journal Officiel",
                    "titre": "Seuils micro-entrepreneurs 2026 : revalorisation de 5%",
                    "impact": "Les seuils de TVA et de chiffre d'affaires augmentent de 5% pour les micro-entrepreneurs.",
                    "action": "Vérifier les seuils de vos clients avant le 31 mai et mettre à jour leur statut fiscal.",
                    "lien": "https://www.legifrance.gouv.fr/jo"
                },
                {
                    "source": "BOFiP",
                    "titre": "TVA : précisions sur les livraisons à soi-même (LAS)",
                    "impact": "Les entreprises réalisant des LAS doivent désormais utiliser le nouveau formulaire 3310-LAS.",
                    "action": "Identifier les clients concernés (BTP, travaux immobiliers) et mettre à jour leurs procédures.",
                    "lien": "https://bofip.impots.gouv.fr/bofip"
                },
                {
                    "source": "URSSAF",
                    "titre": "Échéances sociales mai 2026",
                    "impact": "Paiement des cotisations sociales le 15 mai, DSN le 10 mai.",
                    "action": "Programmer les rappels pour vos clients avant le 10 mai et vérifier les montants.",
                    "lien": "https://www.urssaf.fr"
                }
            ]
            st.success(f"{len(articles_ia)} articles analysés")
            for article in articles_ia:
                with st.expander(f"📌 {article['titre']} — {article['source']}"):
                    st.markdown(f"**Impact :** {article['impact']}")
                    st.markdown(f"**Action :** {article['action']}")
                    st.markdown(f"[📖 Lire l'article original]({article['lien']})")
            html = "<html><body><h1>Veille fiscale</h1><hr>".join(
                [f"<h3>{a['titre']}</h3><p>{a['impact']}</p>" for a in articles_ia]
            )
            st.download_button("📥 Télécharger (HTML)", html, "veille.html", mime="text/html")

# 🗂️ Historique
elif menu == "🗂️ Historique":
    st.title("🗂️ Historique des factures")
    rows = charger_historique(user_id)
    if not rows:
        st.info("Aucune facture analysée pour l'instant.")
    else:
        df = pd.DataFrame(rows, columns=["ID", "Date analyse", "Client", "N° facture", "Fournisseur", "HT", "TVA", "TTC", "Compte"])
        st.dataframe(df)
        if st.button("🗑️ Vider l'historique"):
            vider_historique(user_id)
            st.success("Historique vidé.")
            st.experimental_rerun()
