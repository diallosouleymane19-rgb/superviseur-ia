#!/usr/bin/env bash
# Récupère une copie externe et la déchiffre, SANS toucher à la base.
#   sudo bash restaurer_externe.sh              -> liste les copies disponibles
#   sudo bash restaurer_externe.sh NOM.gpg      -> télécharge et déchiffre dans sauvegardes/restauree_NOM
# Le fichier obtenu est une sauvegarde SQL compressée (.sql.gz) ; sa réintégration dans la base
# est une opération à part, à décider au cas par cas.
set -euo pipefail
cd "$(dirname "$0")"
umask 077
set -a; . ./sauvegarde_externe.env; set +a
export RCLONE_CONFIG_OVH_TYPE=s3 RCLONE_CONFIG_OVH_PROVIDER=Other \
       RCLONE_CONFIG_OVH_ENDPOINT="$S3_ENDPOINT" RCLONE_CONFIG_OVH_REGION="$S3_REGION" \
       RCLONE_CONFIG_OVH_ACCESS_KEY_ID="$S3_ACCESS_KEY" RCLONE_CONFIG_OVH_SECRET_ACCESS_KEY="$S3_SECRET_KEY" \
       RCLONE_CONFIG_OVH_NO_CHECK_BUCKET=true
if [ $# -eq 0 ]; then
  rclone lsl "ovh:$S3_BUCKET" | sort -k2,3
  exit 0
fi
nom="$(basename "$1")"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
rclone copyto "ovh:$S3_BUCKET/$nom" "$tmp/$nom"
sortie="sauvegardes/restauree_${nom%.gpg}"
gpg --batch --yes --quiet --pinentry-mode loopback --decrypt --passphrase-file .phrase_sauvegarde -o "$sortie" "$tmp/$nom"
gzip -t "$sortie"
echo "OK : $sortie ($(gzip -cd "$sortie" | grep -c 'CREATE TABLE') tables)"
