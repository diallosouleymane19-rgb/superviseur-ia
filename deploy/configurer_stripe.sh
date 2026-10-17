#!/usr/bin/env bash
# Active le paiement Stripe de KontrolIA (mode test d'abord, puis mode réel avec la clé sk_live_).
#   sudo bash /opt/superviseur/deploy/configurer_stripe.sh
# La clé secrète Stripe est saisie au clavier (rien ne s'affiche) et reste sur le serveur.
# Le script crée les produits, les prix, le portail client et le webhook, puis enregistre le secret du webhook.
set -euo pipefail
cd "$(dirname "$0")"
umask 077

echo "1/4 Clé secrète Stripe (Développeurs > Clés API > Clé secrète, commence par sk_test_ ou sk_live_)"
read -rsp "  Collez la clé (rien ne s'affiche, c'est normal) : " CLE; echo
CLE="$(printf '%s' "$CLE" | tr -d ' \t\r\n"'"'"',')"
if ! [[ "$CLE" =~ ^(sk|rk)_(test|live)_[A-Za-z0-9]{20,}$ ]]; then
  echo "  Ce n'est pas une clé secrète Stripe (${#CLE} caractères, commence par ${CLE:0:3}…). Rien n'est modifié."
  echo "  La clé publiable (pk_…) ne convient pas : il faut la clé SECRÈTE (sk_…)."
  exit 1
fi
MODE=$([[ "$CLE" == *_test_* ]] && echo "TEST" || echo "RÉEL")
echo "  Clé reconnue : mode $MODE, ${#CLE} caractères."

echo "2/4 Enregistrement dans secrets.toml"
cp secrets.toml "sauvegardes/secrets.toml.avant-stripe.$(date +%Y%m%d%H%M%S)"
grep -v -E '^(STRIPE_SECRET_KEY|STRIPE_WEBHOOK_SECRET)[[:space:]]*=' secrets.toml > secrets.toml.tmp || true
printf "STRIPE_SECRET_KEY = '%s'\n" "$CLE" >> secrets.toml.tmp
cat secrets.toml.tmp > secrets.toml      # même fichier (droits et propriétaire conservés)
rm -f secrets.toml.tmp
unset CLE
docker compose up -d --force-recreate app webhook > /dev/null 2>&1
sleep 8

echo "3/4 Produits, prix, portail client et webhook dans Stripe"
docker compose exec -T app python scripts/stripe_initialiser.py > webhook.tmp
grep -q '^STRIPE_WEBHOOK_SECRET = "whsec_' webhook.tmp || { echo "  ÉCHEC : secret du webhook non reçu."; rm -f webhook.tmp; exit 1; }
cat webhook.tmp >> secrets.toml
rm -f webhook.tmp
docker compose up -d --force-recreate app webhook > /dev/null 2>&1
sleep 8

echo "4/4 Vérification du point de réception"
URL="$(sed -n "s/^APP_URL *= *[\"']\(.*\)[\"']/\1/p" secrets.toml | head -1)"
CODE="$(curl -s -o /dev/null -w '%{http_code}' -X POST "$URL/webhook/stripe" || true)"
if [ "$CODE" = "400" ]; then
  echo "  $URL/webhook/stripe répond (requête non signée refusée, c'est le comportement attendu)."
else
  echo "  ATTENTION : $URL/webhook/stripe a répondu $CODE au lieu de 400."
fi
echo "✅ Stripe configuré en mode $MODE. Page Abonnement : les boutons de paiement sont actifs."
