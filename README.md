# 🏠 Superviseur IA Comptable — France 🇫🇷
> **SMD Global Consulting LLC** | Comptable Augmenté par Intelligence Artificielle

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://superviseur-ia-kfn9tkvdpge3zihtthwaqm.streamlit.app/)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![Mistral AI](https://img.shields.io/badge/AI-Mistral-orange)
![PCG](https://img.shields.io/badge/Norme-PCG%20France-blue)
![License](https://img.shields.io/badge/License-Proprietary-red)

---

## 🎯 Présentation

Le **Superviseur IA Comptable** est une plateforme professionnelle d'audit et de supervision comptable augmentée par Intelligence Artificielle, développée par **SMD Global Consulting LLC**.

Conçu pour les **experts-comptables**, **DAF** et **TPE/PME françaises**, il automatise les tâches chronophages du cycle comptable tout en garantissant la conformité aux normes **PCG** et **DGFiP**.

> Version Afrique francophone (SYSCOHADA, FCFA) : dépôt séparé `superviseur-ia-syscohada`.

---

## 🚀 Fonctionnalités — 20 pages

### 🔍 Analyse & Audit
| Module | Fichier |
|--------|---------|
| 🧾 Analyse Facture (OCR) — extraction structurée + conformité Article 242 nonies A CGI | `utils/analyse_facture.py` |
| 📊 Audit Balance — score qualité, anomalies, répartition par classes PCG | `utils/audit_balance.py` |
| 🛡 Loi de Benford — détection statistique (MAD, Chi-carré, Z-score) | `utils/benford_module.py` |
| ⚠ Alertes & Anomalies — contrôles automatiques multi-niveaux | `utils/alertes.py` |
| ✅ Cohérence des Données — vérifications qualité + score sur 100 | `utils/coherence.py` |

### 📈 États Financiers
| Module | Fichier |
|--------|---------|
| 📈 Compte de Résultat — SIG selon PCG | `utils/compte_resultat.py` |
| 📊 Bilan Comptable — FDR, BFR, trésorerie nette | `utils/bilan.py` |
| 🔄 Rapprochement Bancaire — matching montant + date + libellé | `utils/rapprochement.py` |
| 📦 Immobilisations — amortissement linéaire/dégressif, cessions | `utils/immobilisations.py` |
| 📋 Inventaire & Clôture — provisions, régularisations, stocks | `utils/inventaire.py` |
| 📐 Plan de Financement | `utils/plan_financement.py` |
| 💹 TFT Trésorerie | `utils/tft.py` |
| 📊 Comparatif N/N-1 | `utils/comparatif.py` |
| 🧾 Aide TVA CA3/CA12 | `utils/tva.py` |

### 📁 Supervision & Reporting
| Module | Fichier |
|--------|---------|
| 📂 Traitement FEC — conformité DGFiP (Article L.47 A du LPF) | `utils/fec.py` |
| 📋 Rapport Client — livrable avec KPIs, export Word | `utils/rapport_client.py` |
| 📰 Veille Fiscale — flux RSS + calendrier fiscal | `utils/veille_fiscale.py` |

### 🔌 Connecteurs ERP
Page `utils/page_connectors.py`. Connecteurs présents dans `utils/connectors/` : **Sage, Cegid, Pennylane, Odoo, QuickBooks** (classe commune `BaseConnector`).

### ⚙️ Paramètres
| Page | Fichier |
|------|---------|
| 💳 Tarifs & Abonnement (Stripe) | `utils/page_tarifs.py`, `utils/stripe_billing.py` |
| 🔒 Confidentialité & Sécurité | `app.py` |

Plus la page **🏠 Accueil** (KPIs Supabase, accès rapide, statut plateforme).

---

## 🛠️ Stack Technique

| Composant | Technologie |
|-----------|-------------|
| Interface | Streamlit (`app.py`) |
| Langage | Python 3.11 (`runtime.txt`) |
| IA | Mistral AI — `mistral-large-latest` (principal), `mistral-medium-latest` (secours) — `utils/ai.py` |
| Base de données | Supabase PostgreSQL — `utils/db_supabase.py`, `utils/auth_rbac.py` |
| Authentification | bcrypt + rôles (RBAC) — `auth.py` |
| Paiement | Stripe — `utils/stripe_billing.py` + serveur webhook FastAPI `webhook_stripe.py` |
| Exports | Word (`python-docx`), PDF (`reportlab`) |
| Graphiques | Plotly, Matplotlib |

Dépendances complètes : `requirements.txt`.

---

## 👥 Rôles et plans

**Rôles** (`utils/auth_rbac.py`) : `admin`, `cabinet`, `collaborateur`, `client`, `demo`.
Un bouton **« Accès Démonstration »** sur l'écran de connexion ouvre le rôle `demo` (sauvegarde désactivée).

**Plans et quotas d'analyses** :

| Plan | Quota |
|------|-------|
| Gratuit (`free`) | 10 |
| Starter | 50 |
| Pro | 200 |
| Entreprise | illimité |

---

## 🔐 Secrets à configurer

Dans **Streamlit Cloud → Settings → Secrets** (ou `.streamlit/secrets.toml` en local, jamais sur GitHub) :

```toml
MISTRAL_API_KEY       = "..."

SUPABASE_URL          = "https://VOTRE_PROJET.supabase.co"
SUPABASE_SERVICE_KEY  = "..."   # usage serveur uniquement

AUTH_EMAIL            = "..."   # compte admin de secours
AUTH_PASSWORD         = "..."
AUTH_ROLE             = "admin"
AUTH_NOM              = "SMD Global Consulting LLC"

STRIPE_SECRET_KEY     = "..."
STRIPE_WEBHOOK_SECRET = "..."
APP_URL               = "https://superviseur-ia-kfn9tkvdpge3zihtthwaqm.streamlit.app/"
```

---

## 💻 Lancer en local

```bash
git clone https://github.com/diallosouleymane19-rgb/superviseur-ia.git
cd superviseur-ia
pip install -r requirements.txt
streamlit run app.py
```

L'application s'ouvre sur `http://localhost:8501`.

---

## ☁️ Déploiement

Voir **`DEPLOIEMENT.md`** : Streamlit Cloud, Stripe (produits, webhook), checklist de mise en ligne.

---

## 📂 Structure du projet

```
superviseur-ia/
├── app.py               # Application Streamlit (navigation + pages)
├── auth.py              # Connexion / déconnexion
├── webhook_stripe.py    # Serveur webhook Stripe (FastAPI)
├── utils/               # Modules métier + connecteurs ERP
├── scripts/             # Outils annexes
├── tests/               # Fichiers de test (FEC, balance)
├── requirements.txt
└── runtime.txt
```

---

## 📜 Licence

Logiciel propriétaire — © 2026 SMD Global Consulting LLC — Souleymane Diallo.
Contact : contact@smdconsulting.pro
