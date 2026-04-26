import streamlit as st
import requests
import json
from datetime import datetime

st.set_page_config(page_title="Superviseur IA", page_icon="🤖", layout="centered")

st.title("🤖 Superviseur IA - Agent Comptable")
st.caption("SMD Consulting - Souleymane Diallo")
st.divider()

API_KEY = "WGJJsSrYZxx1Ue5gHrUxRnIBKwYVBB9N"

st.subheader("📄 Saisie de la facture")

exemple = """CARREFOUR MARKET
Ticket n° 12345
Date: 25/04/2026
Montant TTC: 45.50 €"""

texte_facture = st.text_area("Collez le texte de la facture :", value=exemple, height=150)

if st.button("🔍 Analyser", type="primary"):
    if not texte_facture:
        st.error("Veuillez entrer une facture")
    else:
        with st.spinner("🤖 Analyse en cours par l'IA..."):
            try:
                url = "https://api.mistral.ai/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {API_KEY}"
                }
                data = {
                    "model": "mistral-small-latest",
                    "messages": [
                        {"role": "system", "content": "Extrais au format JSON strict: num_facture, date, fournisseur, montant_ht, tva, montant_ttc"},
                        {"role": "user", "content": texte_facture}
                    ],
                    "response_format": {"type": "json_object"}
                }
                
                response = requests.post(url, headers=headers, json=data)
                result = response.json()
                infos = json.loads(result["choices"][0]["message"]["content"])
                
                st.success("✅ Facture analysée avec succès !")
                st.divider()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("📛 Fournisseur", infos.get("fournisseur", "?"))
                    st.metric("📅 Date", infos.get("date", "?"))
                    st.metric("🧾 N° facture", infos.get("num_facture", "?"))
                with col2:
                    st.metric("💰 Montant HT", f"{infos.get('montant_ht', 0):.2f} €")
                    st.metric("📊 TVA (20%)", f"{infos.get('tva', 0):.2f} €")
                    st.metric("💶 Montant TTC", f"{infos.get('montant_ttc', 0):.2f} €")
                
                with st.expander("📝 Voir l'écriture comptable"):
                    st.code(f"""
Journal ACH
-----------------------------------------------------------------
{infos.get('montant_ht', 0):.2f} €  →  Compte 606300  (Achats de fournitures)
{infos.get('tva', 0):.2f} €   →  Compte 445660  (TVA déductible 20%)
{infos.get('montant_ttc', 0):.2f} €  ←  Compte 401000  (Fournisseur)
""")
                
                # Génération du fichier FEC
                fec_content = f"""Journal;Compte;Libellé;Débit;Crédit;Date
ACH;606300;{infos.get('fournisseur', '')};{infos.get('montant_ht', 0)};0;{infos.get('date', '')}
ACH;445660;TVA déductible 20%;{infos.get('tva', 0)};0;{infos.get('date', '')}
ACH;401000;{infos.get('fournisseur', '')};0;{infos.get('montant_ttc', 0)};{infos.get('date', '')}"""
                
                st.download_button(
                    label="📥 Télécharger le fichier FEC (CSV)",
                    data=fec_content,
                    file_name=f"FEC_{infos.get('num_facture', 'facture')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
                
            except Exception as e:
                st.error(f"Erreur lors de l'analyse : {str(e)}")
