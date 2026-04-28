# 🤖 Superviseur IA – SaaS Comptable  
### SMD Consulting – par Souleymane Diallo

Superviseur IA est une application SaaS développée avec Streamlit.  
Elle automatise l’analyse de factures, la génération de FEC conformes DGFiP, la détection d’anomalies comptables et la veille fiscale.

---

## 🚀 Fonctionnalités principales

### 📄 Analyse automatique des factures
- OCR (image → texte) via Mistral AI  
- Extraction automatique : numéro, date, fournisseur, HT, TVA, TTC  
- Suggestion du compte comptable (PCG France)  
- Génération d’un **FEC 100% conforme DGFiP**  
- Historique par utilisateur

### 👥 Multi‑utilisateurs (SaaS)
- Création de compte  
- Connexion sécurisée (hash PBKDF2)  
- Données isolées par utilisateur  
- Multi‑dossiers clients

### 🔍 Détection d’anomalies
- Import CSV / Excel  
- Détection des montants supérieurs à un seuil  
- Export CSV

### 📰 Veille fiscale
- Synthèse hebdomadaire  
- Sources : JO, BOFiP, URSSAF  
- Export HTML

---

## 🛠️ Installation

```bash
pip install -r requirements.txt

