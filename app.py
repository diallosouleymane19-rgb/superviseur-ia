import streamlit as st
import requests
import json
import base64
from datetime import datetime

st.set_page_config(page_title="Superviseur IA", page_icon="🤖", layout="centered")

st.title("🤖 Superviseur IA - Agent Comptable")
st.caption("SMD Consulting - Souleymane Diallo")
st.divider()

API_KEY = "WGJJsSrYZxx1Ue5gHrUxRnIBKwYVBB9N"

# Mode de saisie
mode = st.radio("Mode de saisie", ["📝 Texte manuel", "📎 Upload PDF/Image"])

st.subheader("📄 Saisie de la facture")

texte_facture = ""

if mode == "📝 Texte manuel":
    exemple = """CARREFOUR MARKET
Ticket n° 12345
Date: 25/04/2026
Montant TTC: 45.50 €"""
    texte_facture = st.text_area("Collez le texte de la facture :", value=exemple, height=150)

else:  # Mode Upload
    fichier = st.file_uploader("Choisissez un fichier (PDF, JPG, PNG)", type=["pdf", "jpg", "jpeg", "png"])
    
    if fichier is not None:
        st.success(f"✅ Fichier chargé : {fichier.name}")
        bytes_data = fichier.read()
        base64_data = base64.b64encode(bytes_data).decode()
        
        if fichier.type == "application/pdf":
            mime_type = "application/pdf"
        else:
            mime_type = "image/jpeg"
        
        with st.spinner("🔍 Extraction du texte par IA..."):
            url = "https://api.mistral.ai/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}"
            }
            data = {
                "model": "mistral-small-latest",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extrais le texte brut de cette facture."},
                            {"type": "image_url", "image_url": f"data:{mime_type};base64,{base64_data}"}
                        ]
                    }
                ]
            }
            try:
                response = requests.post(url, headers=headers, json=data)
                result = response.json()
                texte_facture = result["choices"][0]["message"]["content"]
                st.success("📄 Texte extrait avec succès !")
                with st.expander("Voir le texte extrait"):
                    st.text(texte_facture)
            except Exception as e:
                st.error(f"Erreur: {e}")

if st.button("🔍 Analyser", type="primary"):
    if not texte_facture:
        st.error("Veuillez entrer une facture")
    else:
        with st.spinner("Analyse en cours..."):
            try:
                url = "https://api.mistral.ai/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {API_KEY}"
                }
                data = {
                    "model": "mistral-small-latest",
                    "messages": [
                        {"role": "system", "content": "Extrais au format JSON: num_facture, date, fournisseur, montant_ht, tva, montant_ttc"},
                        {"role": "user", "content": texte_facture}
                    ],
                    "response_format": {"type": "json_object"}
                }
                response = requests.post(url, headers=headers, json=data)
                result = response.json()
                infos = json.loads(result["choices"][0]["message"]["content"])
                
                st.success("✅ Facture analysée !")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Fournisseur", infos.get("fournisseur", "?"))
                    st.metric("Date", infos.get("date", "?"))
                with col2:
                    st.metric("Montant HT", f"{infos.get('montant_ht', 0)} €")
                    st.metric("TTC", f"{infos.get('montant_ttc', 0)} €")
                
                fec = f"""Journal;Compte;Libellé;Débit;Crédit;Date
ACH;606300;{infos.get('fournisseur', '')};{infos.get('montant_ht', 0)};0;{infos.get('date', '')}
ACH;445660;TVA;{infos.get('tva', 0)};0;{infos.get('date', '')}
ACH;401000;{infos.get('fournisseur', '')};0;{infos.get('montant_ttc', 0)};{infos.get('date', '')}"""
                
                st.download_button("📥 Télécharger FEC", fec, f"FEC_{infos.get('num_facture', 'facture')}.csv")
            except Exception as e:
                st.error(f"Erreur: {e}")
