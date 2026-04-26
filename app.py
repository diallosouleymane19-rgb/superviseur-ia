import streamlit as st
import requests
import json
import base64
from datetime import datetime
import io
from PIL import Image

st.set_page_config(page_title="Superviseur IA", page_icon="🤖", layout="centered")

st.title("🤖 Superviseur IA - Agent Comptable")
st.caption("SMD Consulting - Souleymane Diallo")
st.divider()

API_KEY = "WGJJsSrYZxx1Ue5gHrUxRnIBKwYVBB9N"

# Mode de saisie
mode = st.radio("Mode de saisie", ["📝 Texte manuel", "📎 Upload Image (JPG/PNG)"])

st.subheader("📄 Saisie de la facture")

texte_facture = ""

if mode == "📝 Texte manuel":
    exemple = """CARREFOUR MARKET
Ticket n° 12345
Date: 25/04/2026
Montant TTC: 45.50 €"""
    texte_facture = st.text_area("Collez le texte de la facture :", value=exemple, height=150)

else:  # Mode Upload
    st.info("⚠️ Pour les PDF, utilisez d'abord un convertisseur en ligne (PDF → JPG) ou le mode texte.")
    fichier = st.file_uploader("Choisissez une image (JPG, PNG)", type=["jpg", "jpeg", "png"])
    
    if fichier is not None:
        st.success(f"✅ Fichier chargé : {fichier.name}")
        
        # Afficher l'image uploadée
        image = Image.open(fichier)
        st.image(image, caption="Facture uploadée", width=300)
        
        # Convertir en base64
        bytes_data = fichier.getvalue()
        base64_data = base64.b64encode(bytes_data).decode()
        
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
                            {
                                "type": "text",
                                "text": "Extrais TOUT le texte de cette facture. Retourne UNIQUEMENT le texte, sans commentaires."
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
                    st.success("📄 Texte extrait avec succès !")
                    with st.expander("Voir le texte extrait"):
                        st.text(texte_facture[:500] + "..." if len(texte_facture) > 500 else texte_facture)
                else:
                    st.error(f"Réponse inattendue: {result}")
                    
            except Exception as e:
                st.error(f"Erreur extraction: {str(e)}")

if st.button("🔍 Analyser", type="primary"):
    if not texte_facture.strip():
        st.error("Veuillez entrer ou uploader une facture")
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
                        {"role": "system", "content": "Extrais au format JSON: num_facture, date, fournisseur, montant_ht, tva, montant_ttc. Si seul le TTC est donné, calcule HT = TTC/1.2 et TVA = TTC - HT."},
                        {"role": "user", "content": texte_facture[:4000]}
                    ],
                    "response_format": {"type": "json_object"}
                }
                response = requests.post(url, headers=headers, json=data, timeout=30)
                result = response.json()
                infos = json.loads(result["choices"][0]["message"]["content"])
                
                st.success("✅ Facture analysée !")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Fournisseur", infos.get("fournisseur", "?"))
                    st.metric("Date", infos.get("date", "?"))
                with col2:
                    st.metric("Montant HT", f"{float(infos.get('montant_ht', 0)):.2f} €")
                    st.metric("TTC", f"{float(infos.get('montant_ttc', 0)):.2f} €")
                
                fec = f"""Journal;Compte;Libellé;Débit;Crédit;Date
ACH;606300;{infos.get('fournisseur', '')};{float(infos.get('montant_ht', 0))};0;{infos.get('date', '')}
ACH;445660;TVA;{float(infos.get('tva', 0))};0;{infos.get('date', '')}
ACH;401000;{infos.get('fournisseur', '')};0;{float(infos.get('montant_ttc', 0))};{infos.get('date', '')}"""
                
                st.download_button("📥 Télécharger FEC", fec, f"FEC_{infos.get('num_facture', 'facture')}.csv")
            except Exception as e:
                st.error(f"Erreur: {e}")
