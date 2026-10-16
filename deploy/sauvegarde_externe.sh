#!/usr/bin/env bash
# Copie chiffrée de la dernière sauvegarde vers l'Object Storage OVH (autre centre de données que le serveur).
# Lancée par sauvegarde.sh. Chiffrement AES-256 (gpg) avec la phrase secrète de .phrase_sauvegarde :
# sans cette phrase, les copies sont illisibles, y compris par OVH. Copies gardées 14 jours.
# Configuration : sudo bash configurer_sauvegarde_externe.sh
set -euo pipefail
cd "$(dirname "$0")"
umask 077
CONF=sauvegarde_externe.env
PHRASE=.phrase_sauvegarde
if [ ! -f "$CONF" ] || [ ! -f "$PHRASE" ]; then
  echo "$(date '+%F %T') Copie externe non configurée : ignorée"
  exit 0
fi
set -a; . "./$CONF"; set +a
export RCLONE_CONFIG_OVH_TYPE=s3 RCLONE_CONFIG_OVH_PROVIDER=Other \
       RCLONE_CONFIG_OVH_ENDPOINT="$S3_ENDPOINT" RCLONE_CONFIG_OVH_REGION="$S3_REGION" \
       RCLONE_CONFIG_OVH_ACCESS_KEY_ID="$S3_ACCESS_KEY" RCLONE_CONFIG_OVH_SECRET_ACCESS_KEY="$S3_SECRET_KEY" \
       RCLONE_CONFIG_OVH_NO_CHECK_BUCKET=true

dernier="$(ls -1t sauvegardes/smd_*.sql.gz 2>/dev/null | head -1)"
[ -n "$dernier" ] || { echo "$(date '+%F %T') ÉCHEC copie externe : aucune sauvegarde locale" >&2; exit 1; }
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
chiffre="$tmp/$(basename "$dernier").gpg"
gpg --batch --yes --quiet --pinentry-mode loopback --symmetric --cipher-algo AES256 \
    --passphrase-file "$PHRASE" -o "$chiffre" "$dernier"
rclone copyto --retries 3 "$chiffre" "ovh:$S3_BUCKET/$(basename "$chiffre")"
# Contrôle : la copie distante a la même taille que le fichier chiffré
distant="$(rclone size --json "ovh:$S3_BUCKET/$(basename "$chiffre")" | sed -n 's/.*"bytes":\([0-9]*\).*/\1/p')"
[ "$distant" = "$(stat -c %s "$chiffre")" ] || { echo "$(date '+%F %T') ÉCHEC copie externe : taille différente" >&2; exit 1; }
rclone delete --min-age 14d --include 'smd_*.sql.gz.gpg' "ovh:$S3_BUCKET"
echo "$(date '+%F %T') OK copie externe : $(basename "$chiffre") ($distant octets) vers $S3_BUCKET"
