# Guide de Déploiement — SMD Consulting
## Superviseur IA PCG France + RevisionPro SYSCOHADA

---

## 1. Prérequis

- Compte GitHub (gratuit) : https://github.com
- Compte Streamlit Cloud (gratuit) : https://share.streamlit.io
- Compte Stripe (test d'abord) : https://dashboard.stripe.com
- Clé Mistral AI : https://console.mistral.ai

---

## 2. GitHub — Pousser les deux apps

### 2.1 Superviseur IA PCG France

```bash
cd C:\Users\blois\superviseur-ia

# Initialiser Git si pas encore fait
git init
git add .
git commit -m "feat: RBAC + Stripe Billing + Page tarifs + Inscription"

# Créer le repo sur GitHub (nom suggéré : superviseur-ia-pcg)
# Puis :
git remote add origin https://github.com/VOTRE_USERNAME/superviseur-ia-pcg.git
git branch -M main
git push -u origin main
```

### 2.2 RevisionPro SYSCOHADA

```bash
cd C:\Users\blois\superviseur-ia-syscohada

git init
git add .
git commit -m "feat: RBAC + Stripe + Page tarifs + Inscription SYSCOHADA"

git remote add origin https://github.com/VOTRE_USERNAME/revisiopro-syscohada.git
git branch -M main
git push -u origin main
```

> ⚠️ `.gitignore` exclut automatiquement `.streamlit/secrets.toml` — vos clés API restent locales.

---

## 3. Streamlit Cloud — Déploiement

### 3.1 Pour chaque application :

1. Aller sur https://share.streamlit.io
2. Cliquer **"New app"**
3. Connecter votre compte GitHub
4. Sélectionner le repo (`superviseur-ia-pcg` ou `revisiopro-syscohada`)
5. **Main file path** : `app.py`
6. Cliquer **"Deploy"**

### 3.2 Configurer les Secrets dans Streamlit Cloud

Une fois déployé, aller dans **Settings → Secrets** et coller :

**PCG France :**
```toml
MISTRAL_API_KEY = "votre_cle_mistral_pcg_ici"

AUTH_EMAIL    = "votre_email_admin"
AUTH_PASSWORD = "votre_mot_de_passe_admin"
AUTH_ROLE     = "admin"
AUTH_NOM      = "SMD Consulting"

STRIPE_SECRET_KEY     = "sk_live_VOTRE_CLE_LIVE"
STRIPE_WEBHOOK_SECRET = "whsec_VOTRE_SECRET"
APP_URL = "https://superviseur-ia-pcg.streamlit.app"
```

**SYSCOHADA :**
```toml
MISTRAL_API_KEY = "votre_cle_mistral_syscohada_ici"

[users]
smdconsulting = "votre_mot_de_passe"

STRIPE_SECRET_KEY     = "sk_live_VOTRE_CLE_LIVE"
STRIPE_WEBHOOK_SECRET = "whsec_VOTRE_SECRET"
APP_URL = "https://revisiopro-syscohada.streamlit.app"
```

---

## 4. Stripe — Configuration

### 4.1 Créer les produits (Dashboard Stripe)

1. Aller sur https://dashboard.stripe.com/products
2. Créer 3 produits : **Starter**, **Pro**, **Entreprise**
3. Pour chaque produit, créer 2 prix : mensuel et annuel
4. Copier les **Price IDs** (format `price_xxx`)
5. Les mettre à jour dans `utils/stripe_billing.py` → variable `STRIPE_PRICES`

### 4.2 Configurer le Webhook

1. Dashboard Stripe → **Webhooks** → **Add endpoint**
2. URL : `https://VOTRE-DOMAINE/webhook/stripe`
   - En développement : utiliser **ngrok** (`ngrok http 4242`)
   - En production : déployer `webhook_stripe.py` sur Railway/Render
3. Événements à écouter :
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`
4. Copier le **Webhook signing secret** → `STRIPE_WEBHOOK_SECRET`

### 4.3 Déployer le serveur webhook (Railway — gratuit)

```bash
# Depuis le dossier superviseur-ia
railway login
railway new
railway up --service webhook

# Variables d'environnement Railway :
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
```

---

## 5. Checklist finale avant mise en ligne

- [ ] Clés Mistral AI actives (pas expirées)
- [ ] Clé Stripe LIVE (pas test) dans Streamlit Secrets
- [ ] Price IDs Stripe mis à jour dans `utils/stripe_billing.py`
- [ ] Webhook Stripe configuré et testé
- [ ] APP_URL correct (URL Streamlit Cloud réelle)
- [ ] Admin connecté, inscription testée
- [ ] Paiement test effectué sur un plan Starter
- [ ] Quota incrémenté après analyse (vérifier `smd_users.db`)
- [ ] Audit logs actifs
- [ ] `.gitignore` vérifié (pas de secrets sur GitHub)

---

## 6. URLs de production (à personnaliser)

| App | URL Streamlit | Webhook |
|-----|--------------|---------|
| PCG France | `https://superviseur-ia-pcg.streamlit.app` | `https://webhook-pcg.railway.app/webhook/stripe` |
| SYSCOHADA | `https://revisiopro-syscohada.streamlit.app` | `https://webhook-sysc.railway.app/webhook/stripe` |

---

## 7. Support & Maintenance

- Email : contact@smdconsulting.pro
- Logs Streamlit Cloud : onglet **Logs** dans le dashboard
- Audit logs app : page **Admin → Utilisateurs**
- Quota usage : base `smd_users.db` → table `smd_quota_usage`

---

*SMD Consulting LLC — Wyoming USA — Opéré depuis Blois, France*
*© 2026 Souleymane Diallo*
