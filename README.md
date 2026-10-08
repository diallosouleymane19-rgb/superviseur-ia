# 🏠 Superviseur IA Comptable — France 🇫🇷
> **SMD Global Consulting LLC** | Comptable Augmenté par Intelligence Artificielle

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://superviseur-ia-kfn9tkvdpge3zihtthwaqm.streamlit.app/)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![Mistral AI](https://img.shields.io/badge/AI-Mistral-orange)
![PCG](https://img.shields.io/badge/Norme-PCG%20France-blue)
![License](https://img.shields.io/badge/License-Proprietary-red)

---

## 🎯 Présentation

Le **Superviseur IA Comptable** est une plateforme d'audit et de supervision comptable développée par **SMD Global Consulting LLC**, destinée aux **professionnels** : experts-comptables, DAF, TPE/PME françaises.

Les traitements comptables (écritures, bilan, SIG, contrôles) sont calculés **par des règles PCG, sans IA**. L'IA (Mistral) sert uniquement à rédiger des commentaires et des analyses, toujours signalés comme générés par IA.

> Version Afrique francophone (SYSCOHADA, FCFA) : application distincte, dépôt séparé `superviseur-ia-syscohada`.

---

## 🚀 Fonctionnalités — 21 pages

### 🔍 Analyse & Contrôle
| Module | Fichier |
|--------|---------|
| 🧾 Analyse et comptabilisation de factures — voir détail ci-dessous | `utils/analyse_facture.py`, `utils/compta_facture.py`, `utils/facture_electronique.py` |
| 📊 Contrôle de balance — score qualité, anomalies, répartition par classes PCG | `utils/audit_balance.py` |
| 🛡 Loi de Benford — détection statistique (MAD, Chi-carré, Z-score) | `utils/benford_module.py` |
| ⚠ Alertes & Anomalies — contrôles automatiques multi-niveaux | `utils/alertes.py` |
| ✅ Cohérence des Données — vérifications qualité + score sur 100 | `utils/coherence.py` |

### 📈 États Financiers
| Module | Fichier |
|--------|---------|
| 📈 Compte de Résultat — SIG selon PCG | `utils/compte_resultat.py` |
| 📊 Bilan Comptable — brut / amortissements / net, FRNG, BFR, trésorerie nette, ratios | `utils/bilan.py` |
| 🔄 Rapprochement Bancaire — rapprochement par montant, date et libellé | `utils/rapprochement.py` |
| 📦 Immobilisations — amortissement linéaire/dégressif, cessions | `utils/immobilisations.py` |
| 📋 Inventaire & Clôture — provisions, régularisations, stocks | `utils/inventaire.py` |
| 📐 Plan de Financement | `utils/plan_financement.py` |
| 💹 TFT Trésorerie | `utils/tft.py` |
| 📊 Comparatif N/N-1 | `utils/comparatif.py` |
| 🧾 Aide TVA CA3/CA12 | `utils/tva.py` |

### 📁 Supervision & Reporting
| Module | Fichier |
|--------|---------|
| 📂 Traitement FEC — conformité DGFiP (article L.47 A du LPF) | `utils/fec.py` |
| 📋 Rapport Client — livrable avec indicateurs, export Word | `utils/rapport_client.py` |
| 📰 Veille Fiscale — flux RSS, calendrier fiscal, analyse IA facultative | `utils/veille_fiscale.py` |

### 🔌 Connecteurs ERP
Page `utils/page_connectors.py`. Connecteurs présents dans `utils/connectors/` : **Sage, Cegid, Pennylane, Odoo, QuickBooks** (classe commune `BaseConnector`).

### ⚙️ Paramètres
| Page | Fichier |
|------|---------|
| 💳 Tarifs & Abonnement (Stripe) | `utils/page_tarifs.py`, `utils/stripe_billing.py` |
| 🔒 Confidentialité & Sécurité | `app.py` |

Plus la page **🏠 Accueil** (indicateurs, accès rapide, échéances). Les **CGU** et la **politique de confidentialité** s'ouvrent sans connexion : `?doc=cgu` et `?doc=confidentialite` (`utils/pages_legales.py`).

### Formats de fichiers acceptés
- **Balances, FEC, relevés** : CSV, TXT, Excel `.xlsx` / `.xlsm` / `.xls`, LibreOffice `.ods` (`utils/formats.py`).
- **Factures** : PDF (texte ou scanné), XML, TXT, CSV, photos JPG / PNG.

---

## 🧾 Analyse et comptabilisation de factures

Fonctionne **sans API et sans abonnement** : lecture locale, extraction et imputation par règles PCG.

| Entrée | Lecture |
|--------|---------|
| Factur-X (PDF avec XML joint), XML **CII** ou **UBL** | Données lues dans le XML : montants exacts, sans OCR |
| PDF issu d'un logiciel, fichier texte | Extraction par règles |
| PDF scanné, photo | OCR **Tesseract**, gratuit et local (alerte « à vérifier » systématique) |
| Liste CSV | Une facture par ligne |

Ce que le module traite :
- **Sens** achat / vente selon votre société, **compte proposé** avec sa justification et un niveau de confiance ; compte d'attente 471000 si la nature est inconnue.
- **Ventilation ligne par ligne** : si la somme des lignes d'articles est égale au total HT, chaque ligne peut avoir son propre compte. TVA répartie selon le taux de chaque ligne (ou au prorata), comptes de TVA par nature (445620 / 445800 / 445660), fournisseurs 404 et 401 séparés. Sinon, un seul compte et une alerte si plusieurs natures sont détectées.
- Immobilisation ou charge selon le seuil de **500 € HT** apprécié au prix unitaire.
- TVA sur les services à l'encaissement (445800) ou directe (445660), option pour les débits, **autoliquidation**, franchise en base, exonération, **avoirs**.
- **Factures en devises** : conversion en euros (montant débité ou cours indiqué), colonnes `Montantdevise` / `Idevise` du FEC.
- **Contrôles** : mentions obligatoires (art. 242 nonies A annexe II CGI), SIREN (clé de contrôle), HT + TVA = TTC, cohérence du taux, nouvelles mentions de la facturation électronique (SIREN client, catégorie d'opération, adresse de livraison), net à payer différent du TTC, **doublons**.
- **Exports** : écritures au format FEC, rapport Word.

---

## 🔐 Données personnelles et IA

| Point | Mise en œuvre |
|-------|---------------|
| Hébergement de l'application | Streamlit Community Cloud (Snowflake Inc., États-Unis) |
| Hébergement de la base | Supabase, région UE (Irlande) |
| Fichiers déposés | Lus en mémoire, non enregistrés |
| Analyses sauvegardées | Uniquement sur clic « Sauvegarder », supprimées après **30 jours** |
| Journal des actions et quotas | Supprimés après **12 mois** |
| Comptes gratuits inactifs | Supprimés **3 ans** après la dernière connexion (hors administrateurs) |
| Déclenchement des purges | Automatique, au chargement des pages, au plus une fois par heure (`utils/database.py`) |
| Masquage avant envoi à Mistral | E-mails, IBAN, n° de TVA, SIREN / SIRET, téléphones et nom de l'entreprise remplacés par des repères, remis en clair dans la réponse (`utils/pseudonymisation.py`). Protection partielle : un nom de personne écrit librement n'est pas détecté. |
| Transparence IA (AI Act, art. 50) | Mention « Contenu généré par intelligence artificielle (Mistral AI)… » sur les textes rédigés par l'IA (`utils/page_helpers.py`) |
| Marquage lisible par machine (AI Act, art. 50.2) | À l'écran : bloc `st-key-contenu_ia_…` et élément `data-ai-generated="true"` (fournisseur, modèle, date, type de source IPTC `trainedAlgorithmicMedia`). Exports Word : propriétés du document et propriétés personnalisées `AIGenerated`, `AIProvider`, `AIModel`, `AIGenerationDate`, `DigitalSourceType` (`utils/export_word.py`) |
| Statistiques Streamlit | Désactivées (`.streamlit/config.toml`) |

---

## 🛠️ Stack technique

| Composant | Technologie |
|-----------|-------------|
| Interface | Streamlit (`app.py`) |
| Langage | Python 3.11 (`runtime.txt`) |
| IA | Mistral AI — `mistral-large-latest` (principal), `mistral-medium-latest` (secours) — `utils/ai.py` |
| Base de données | Supabase PostgreSQL — `utils/db_supabase.py`, `utils/database.py`, `utils/auth_rbac.py` |
| Authentification | bcrypt + rôles (RBAC) — `auth.py` |
| Paiement | Stripe — `utils/stripe_billing.py` + serveur webhook FastAPI `webhook_stripe.py` |
| Lecture PDF et Factur-X | PyMuPDF, pypdf |
| OCR | Tesseract (paquets système dans `packages.txt`) + `pytesseract` |
| Tableurs | openpyxl, xlrd (`.xls`), odfpy (`.ods`) |
| Exports | Word (`python-docx`), PDF (`reportlab`) |
| Graphiques | Plotly, Matplotlib |

Dépendances Python : `requirements.txt`. Paquets système (installés par Streamlit Cloud) : `packages.txt`.

---

## 👥 Rôles et plans

**Rôles** (`utils/auth_rbac.py`) : `admin`, `cabinet`, `collaborateur`, `client`, `demo`.
Le bouton **« Essayer la démonstration »** de l'écran de connexion ouvre le rôle `demo` (sauvegarde désactivée).

**Plans et quotas d'analyses par mois** :

| Plan | Quota |
|------|-------|
| Gratuit (`free`) | 10 |
| Starter | 50 |
| Pro | 200 |
| Entreprise | illimité |

---

## 🔑 Secrets à configurer

Dans **Streamlit Cloud → Settings → Secrets** (ou `.streamlit/secrets.toml` en local, jamais sur GitHub) :

```toml
MISTRAL_API_KEY       = "..."

SUPABASE_URL          = "https://VOTRE_PROJET.supabase.co"
SUPABASE_SERVICE_KEY  = "..."   # usage serveur uniquement (SUPABASE_KEY accepté en secours)

AUTH_EMAIL            = "..."   # compte admin de secours
AUTH_PASSWORD         = "..."
AUTH_ROLE             = "admin"
AUTH_NOM              = "SMD Global Consulting LLC"

STRIPE_SECRET_KEY     = "..."
STRIPE_WEBHOOK_SECRET = "..."
APP_URL               = "https://superviseur-ia-kfn9tkvdpge3zihtthwaqm.streamlit.app/"
```

Dans **GitHub → Settings → Secrets → Actions**, pour la tâche qui empêche la mise en pause de Supabase (`.github/workflows/supabase-ping.yml`, tous les 3 jours) : `SUPABASE_URL` et `SUPABASE_ANON_KEY`.

---

## 💻 Lancer en local

```bash
git clone https://github.com/diallosouleymane19-rgb/superviseur-ia.git
cd superviseur-ia
pip install -r requirements.txt
streamlit run app.py
```

L'application s'ouvre sur `http://localhost:8501`.
Pour l'OCR des scans et photos, installer aussi Tesseract (Linux : `sudo apt install tesseract-ocr tesseract-ocr-fra`). Sans Tesseract, les autres fonctions marchent normalement.

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
├── .streamlit/          # Configuration Streamlit (thème, statistiques désactivées)
├── .github/workflows/   # Tâche planifiée Supabase
├── requirements.txt     # Dépendances Python
├── packages.txt         # Paquets système (Tesseract)
└── runtime.txt
```

---

## 📜 Licence

Logiciel propriétaire — © 2026 SMD Global Consulting LLC — Souleymane Diallo.
Contact : contact@smdconsulting.pro
