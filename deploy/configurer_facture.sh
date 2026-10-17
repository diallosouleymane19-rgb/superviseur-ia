#!/usr/bin/env bash
# Identité du vendeur en pied des factures Stripe (siège de la LLC, EIN, établissement en France).
#   sudo bash /opt/superviseur/deploy/configurer_facture.sh
# Relançable : la ligne STRIPE_MENTIONS_VENDEUR de secrets.toml est remplacée.
set -euo pipefail
cd "$(dirname "$0")"
umask 077
echo "Informations du vendeur pour le pied des factures (Entrée pour valider chaque ligne)"
read -rp "  Adresse du siège de la LLC (Wyoming, sur une ligne) : " SIEGE
read -rp "  EIN de la LLC (ex. 12-3456789) : " EIN
read -rp "  Établissement en France (adresse, sur une ligne) : " FRANCE
SIEGE="$(printf '%s' "$SIEGE" | tr -d '"\\')"; FRANCE="$(printf '%s' "$FRANCE" | tr -d '"\\')"
EIN="$(printf '%s' "$EIN" | tr -cd '0-9-')"
[[ "$EIN" =~ ^[0-9]{2}-?[0-9]{7}$ ]] || { echo "  EIN non reconnu (9 chiffres attendus, ex. 12-3456789). Rien n'est modifié."; exit 1; }
[ -n "$SIEGE" ] && [ -n "$FRANCE" ] || { echo "  Adresse vide. Rien n'est modifié."; exit 1; }
TEXTE="SMD GLOBAL CONSULTING LLC, Limited Liability Company de droit du Wyoming (États-Unis) — Siège : $SIEGE — EIN : $EIN — Établissement en France : $FRANCE"
cp secrets.toml "sauvegardes/secrets.toml.avant-facture.$(date +%Y%m%d%H%M%S)"
grep -v -E '^STRIPE_MENTIONS_VENDEUR[[:space:]]*=' secrets.toml > secrets.toml.tmp || true
printf 'STRIPE_MENTIONS_VENDEUR = "%s"\n' "$TEXTE" >> secrets.toml.tmp
cat secrets.toml.tmp > secrets.toml && rm -f secrets.toml.tmp
docker compose up -d --force-recreate app > /dev/null 2>&1
echo "  Pied de facture enregistré :"
echo "  $TEXTE"
echo "✅ Appliqué aux prochaines factures (et aux clients existants à leur prochain passage par l'abonnement)."
