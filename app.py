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
mode = st.radio("Mode de saisie", ["📝 Texte manuel", "📎 Upload Image (JPG, PNG)", "📄 PDF - Copier le texte"])

st.subheader("📄 Saisie de la facture")

texte_facture = ""

if mode == "📝 Texte manuel":
    exemple = """CARREFOUR MARKET
Ticket n° 12345
Date: 25/04/2026
Montant TTC: 45.50 €"""
    texte_facture = st.text_area("Collez le texte de la facture :", value=exemple, height=150)

elif mode == "📄 PDF - Copier le texte":
    st.info("ℹ️ Pour les PDF : ouvrez le fichier, copiez le texte (Ctrl+A, Ctrl+C) et collez-le ci-dessous.")
    texte_facture = st.text_area("Collez le texte extrait du PDF :", height=150)

else:  # Mode Upload Image
    fichier = st.file_uploader("Choisissez une image (JPG, PNG)", type=["jpg", "jpeg", "png"])
    
    if fichier is not None:
        st.success(f"✅ Fichier chargé : {fichier.name}")
        
        # Lire l'image en base64
        bytes_data = fichier.read()
        base64_data = base64.b64encode(bytes_data).decode()
        
        with st.spinner("🔍 OCR en cours..."):
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
                            {
                                "type": "text",
                                "text": "Extrais le texte de cette facture. Retourne UNIQUEMENT le texte brut."
                            },
                            {
                                "type": "image_url",
                                "image_url": f"data:image/jpeg;base64,{base64_data}"
                            }
                        ]
                    }
                ]
            }
            
            try:
                response = requests.post(url, headers=headers, json=data, timeout=30)
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    texte_facture = result["choices"][0]["message"]["content"]
                    st.success("📄 Texte extrait !")
                    with st.expander("Voir le texte extrait"):
                        st.text(texte_facture[:500])
                else:
                    st.error("Erreur OCR")
            except Exception as e:
                st.error(f"Erreur: {str(e)}")

if st.button("🔍 Analyser", type="primary"):
    if not texte_facture.strip():
        st.error("Veuillez entrer le texte de la facture")
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
                        {"role": "system", "content": "Extrais au format JSON: num_facture, date, fournisseur, montant_ht, tva, montant_ttc. Si seul TTC donné, calcule HT = TTC/1.2."},
                        {"role": "user", "content": texte_facture[:4000]}
                    ],
                    "response_format": {"type": "json_object"}
                }
                response = requests.post(url, headers=headers, json=data, timeout=30)
                result = response.json()
                infos = json.loads(result["choices"][0]["message"]["content"])
                
                st.success("✅ Analyse terminée")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Fournisseur", infos.get("fournisseur", "?"))
                    st.metric("Date", infos.get("date", "?"))
                with col2:
                    st.metric("HT", f"{float(infos.get('montant_ht', 0)):.2f} €")
                    st.metric("TTC", f"{float(infos.get('montant_ttc', 0)):.2f} €")
                
                fec = f"""Journal;Compte;Libellé;Débit;Crédit;Date
ACH;606300;{infos.get('fournisseur', '')};{float(infos.get('montant_ht', 0))};0;{infos.get('date', '')}
ACH;445660;TVA;{float(infos.get('tva', 0))};0;{infos.get('date', '')}
ACH;401000;{infos.get('fournisseur', '')};0;{float(infos.get('montant_ttc', 0))};{infos.get('date', '')}"""
                
                st.download_button("📥 Télécharger FEC", fec, f"FEC_{infos.get('num_facture', 'facture')}.csv")
            except Exception as e:
                st.error(f"Erreur: {e}")
