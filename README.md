# 🧠 Superviseur IA Comptable

> **Assistant comptable intelligent propulsé par l'IA Mistral**  
> Développé par **SMD Consulting** — Souleymane DIALLO

---

## 🎯 Présentation

Le **Superviseur IA Comptable** est une application web intelligente qui automatise
l'analyse financière et comptable des entreprises. Développé avec Python et Streamlit,
il intègre l'IA Mistral pour produire des analyses professionnelles en quelques secondes.

Cet outil est conçu pour les **experts-comptables**, **DAF**, **freelances comptables**
et **PME** souhaitant gagner en productivité et en qualité d'analyse.

---

## ✨ Fonctionnalités

| Module | Description |
|--------|-------------|
| 🧾 **OCR Facture** | Extraction automatique du texte et analyse comptable des factures PDF/image |
| 📊 **Analyse Balance** | Analyse IA complète de la balance comptable (anomalies, risques, suggestions) |
| 📂 **Traitement FEC** | Contrôle fiscal du Fichier des Écritures Comptables |
| 💳 **Traitement Factures** | Analyse de fichiers Excel/CSV de factures avec détection d'anomalies |
| 🏦 **Rapprochement Bancaire** | Comparaison automatique relevé bancaire vs écritures comptables |
| 🔗 **Cohérence Inter-Documents** | Croisement et vérification de cohérence entre documents comptables |
| 🚨 **Alertes de Gestion** | Détection d'anomalies et alertes financières en temps réel |
| 📰 **Veille Fiscale** | Actualités fiscales françaises et calendrier des obligations |
| 📋 **Analyse Bilan** | Analyse complète du bilan (ratios, FRNG, BFR, trésorerie nette) |
| 📈 **Compte de Résultat** | SIG, marges, rentabilité et recommandations |
| 📥 **Export HTML** | Téléchargement de chaque analyse en rapport HTML professionnel |

---

## 🚀 Démo en ligne

🔗 **[Accéder à l'application](https://superviseur-ia.streamlit.app)**

> Identifiants de démonstration disponibles sur demande.

---

## 🛠️ Technologies utilisées

- **Python 3.x** — Langage principal
- **Streamlit** — Interface web interactive
- **Mistral AI** — Moteur d'analyse IA (mistral-large-latest)
- **Pandas** — Traitement des données
- **Plotly** — Graphiques interactifs
- **PyPDF2 / pdf2image** — Extraction PDF
- **bcrypt** — Authentification sécurisée
- **GitHub + Streamlit Cloud** — Déploiement continu

---

## 📦 Installation locale

```bash
# 1. Cloner le dépôt
git clone https://github.com/diallosouleymane19-rgb/superviseur-ia
cd superviseur-ia

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Configurer la clé API Mistral
# Créer un fichier .env à la racine :
MISTRAL_API_KEY=votre_clé_api

# 4. Lancer l'application
streamlit run app.py
```
---

## 💡 Cas d'usage

- **Cabinet d'expertise comptable** — Automatiser les analyses répétitives
- **DAF / CFO** — Tableau de bord financier intelligent
- **Freelance comptable** — Offrir un service premium à ses clients
- **PME** — Piloter sa comptabilité sans expertise technique

---

## 📊 Exemples d'analyses générées

### Analyse de Bilan
- Structure Actif/Passif avec ratios financiers
- Calcul FRNG, BFR et Trésorerie Nette
- Recommandations de régularisation

### Analyse FEC
- Détection d'anomalies fiscales
- Vérification de la cohérence des écritures
- Risques de contrôle fiscal identifiés

---

## 👨‍💼 Auteur

**Souleymane DIALLO**  
Étudiant CNAM — DRF100 & CFA010  
Consultant comptable & développeur IA  

📧 Contact : [diallosouleymane19@gmail.com](mailto:diallosouleymane19@gmail.com)  
🔗 GitHub : [diallosouleymane19-rgb](https://github.com/diallosouleymane19-rgb)  
💼 LinkedIn : (https://www.linkedin.com/in/souleymane-diallo-0071205a)
---

## 📄 Licence

Ce projet est développé dans un cadre professionnel et éducatif.  
© 2025 SMD Consulting — Tous droits réservés.

---

> *"L'IA ne remplace pas le comptable, elle le rend 10x plus efficace."*
---

## 🔐 Authentification

L'application est protégée par un système d'authentification sécurisé.  
Les identifiants sont configurables dans le fichier `auth.py`.

---

## 📁 Structure du projet
