import streamlit as st
import requests
import json
import base64
from datetime import datetime

st.set_page_config(page_title="Superviseur IA", page_icon="🤖", layout="centered")

# ==================== MENU ====================
menu = st.sidebar.selectbox("Menu", ["📄 Factures", "📰 Veille fiscale"])

# ==================== FACTURES ====================
if menu == "📄 Factures":
    st.title("🤖 Superviseur IA - Agent Comptable")
    st.caption("SMD Consulting - Souleymane Diallo")
    st.divider()

    API_KEY = "WGJJsSrYZxx1Ue5gHrUxRnIBKwYVBB9N"

    # Initialisation du texte dans session_state
    if "texte_facture" not in st.session_state:
        st.session_state.texte_facture = ""
    if "dernier_mode" not in st.session_state:
        st.session_state.dernier_mode = ""

    # Mode de saisie
    mode = st.radio("Mode de saisie", ["📝 Texte manuel", "📎 Upload Image (JPG, PNG)", "📄 PDF - Copier le texte"])

    st.subheader("📄 Saisie de la facture")

    # Réinitialiser le texte si le mode change
    if mode != st.session_state.dernier_mode:
        st.session_state.texte_facture = ""
        st.session_state.dernier_mode = mode

    # ========== TEXTE MANUEL ==========
    if mode == "📝 Texte manuel":
        exemple = """CARREFOUR MARKET
Ticket n° 12345
Date: 25/04/2026
Montant TTC: 45.50 €"""
        
        texte = st.text_area(
            "Collez le texte de la facture :",
            value=st.session_state.texte_facture if st.session_state.texte_facture else exemple,
            height=150,
            key="texte_manuel"
        )
        st.session_state.texte_facture = texte

    # ========== UPLOAD IMAGE ==========
    elif mode == "📎 Upload Image (JPG, PNG)":
        fichier = st.file_uploader("Choisissez une image", type=["jpg", "jpeg", "png"])
        
        if fichier is not None:
            st.success(f"✅ Fichier chargé : {fichier.name}")
            bytes_data = fichier.read()
            base64_data = base64.b64encode(bytes_data).decode()
            
            with st.spinner("🔍 OCR en cours..."):
                url = "https://api.mistral.ai/v1/chat/completions"
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
                data = {
                    "model": "mistral-small-latest",
                    "messages": [{"role": "user", "content": [{"type": "text", "text": "Extrais le texte de cette facture."}, {"type": "image_url", "image_url": f"data:image/jpeg;base64,{base64_data}"}]}]
                }
                response = requests.post(url, headers=headers, json=data)
                result = response.json()
                texte_extrait = result["choices"][0]["message"]["content"]
                st.session_state.texte_facture = texte_extrait
                st.success("Texte extrait avec succès !")
                st.text_area("Texte extrait :", value=texte_extrait, height=150)

    # ========== PDF ==========
    elif mode == "📄 PDF - Copier le texte":
        st.info("Ouvrez votre PDF, copiez le texte et collez-le ci-dessous.")
        texte = st.text_area(
            "Texte extrait du PDF",
            value=st.session_state.texte_facture,
            height=150,
            key="texte_pdf"
        )
        st.session_state.texte_facture = texte

    # ========== BOUTON ANALYSER ==========
    if st.button("🔍 Analyser", type="primary"):
        texte_a_analyser = st.session_state.texte_facture
        
        if not texte_a_analyser.strip():
            st.error("Veuillez entrer le texte d'une facture")
        else:
            with st.spinner("Analyse en cours..."):
                try:
                    url = "https://api.mistral.ai/v1/chat/completions"
                    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
                    data = {
                        "model": "mistral-small-latest",
                        "messages": [
                            {"role": "system", "content": "Tu es un expert-comptable. Extrais au format JSON: num_facture, date, fournisseur, montant_ht, tva, montant_ttc, compte_suggere. Règles: marchandises→601000, fournitures→606300, services→604000, télécom→626000"},
                            {"role": "user", "content": texte_a_analyser[:4000]}
                        ],
                        "response_format": {"type": "json_object"}
                    }
                    response = requests.post(url, headers=headers, json=data)
                    infos = json.loads(response.json()["choices"][0]["message"]["content"])
                    
                    st.success("✅ Analyse terminée")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Fournisseur", infos.get("fournisseur", "?"))
                        st.metric("Date", infos.get("date", "?"))
                        st.metric("N° facture", infos.get("num_facture", "?"))
                    with col2:
                        st.metric("Montant HT", f"{float(infos.get('montant_ht', 0)):.2f} €")
                        st.metric("TVA", f"{float(infos.get('tva', 0)):.2f} €")
                        st.metric("Montant TTC", f"{float(infos.get('montant_ttc', 0)):.2f} €")
                    
                    # Compte suggéré
                    compte = infos.get("compte_suggere", "606300")
                    st.info(f"📝 Compte comptable suggéré : **{compte}**")
                    
                    # Génération FEC
                    fec = f"""Journal;Compte;Libellé;Débit;Crédit;Date
ACH;{compte};{infos.get('fournisseur', '')};{float(infos.get('montant_ht', 0))};0;{infos.get('date', '')}
ACH;445660;TVA;{float(infos.get('tva', 0))};0;{infos.get('date', '')}
ACH;401000;{infos.get('fournisseur', '')};0;{float(infos.get('montant_ttc', 0))};{infos.get('date', '')}"""
                    
                    st.download_button("📥 Télécharger le fichier FEC", fec, f"FEC_{infos.get('num_facture', 'facture')}.csv")
                    
                except Exception as e:
                    st.error(f"Erreur: {e}")

# ==================== VEILLE FISCALE ====================
elif menu == "📰 Veille fiscale":
    st.title("📰 Veille Fiscale Hebdomadaire")
    st.caption("SMD Consulting - Souleymane Diallo")
    st.divider()
    
    st.markdown("**Analyse automatique des publications officielles (JO, BOFiP, URSSAF)**")
    
    if st.button("📡 Générer la veille de la semaine", type="primary"):
        with st.spinner("🔍 Analyse en cours..."):
            # Simulation d'articles (version démo)
            articles = [
                {"source": "Journal Officiel", "titre": "Seuils micro-entrepreneurs 2026", "date": "22/04/2026", "impact": "Hausse de 5% des seuils", "action": "Vérifier les seuils de vos clients", "lien": "#"},
                {"source": "BOFiP", "titre": "TVA sur livraisons à soi-même", "date": "20/04/2026", "impact": "Nouvelles modalités", "action": "Identifier les clients concernés", "lien": "#"},
                {"source": "URSSAF", "titre": "Échéances sociales mai 2026", "date": "19/04/2026", "impact": "Paiement le 15 mai", "action": "Programmer les rappels", "lien": "#"}
            ]
            
            st.success(f"✅ {len(articles)} articles analysés")
            
            for article in articles:
                with st.expander(f"📌 {article['titre']} - {article['source']} ({article['date']})"):
                    st.markdown(f"""
                    **Impact :** {article['impact']}
                    
                    **Action :** {article['action']}
                    
                    [📖 Lire l'article original]({article['lien']})
                    """)
            
            # Téléchargement
            html = "<html><body>" + "".join([f"<h3>{a['titre']}</h3><p>{a['impact']}</p>" for a in articles]) + "</body></html>"
            st.download_button("📥 Télécharger la veille (HTML)", html, f"veille_{datetime.now().strftime('%Y%m%d')}.html")
