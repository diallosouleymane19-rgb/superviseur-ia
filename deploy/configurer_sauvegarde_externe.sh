#!/usr/bin/env bash
# Configuration unique de la copie externe des sauvegardes (Object Storage OVH, Roubaix).
#   sudo bash /opt/superviseur/deploy/configurer_sauvegarde_externe.sh
# Les clés S3 sont saisies au clavier (rien ne s'affiche) et restent sur le serveur.
set -euo pipefail
cd "$(dirname "$0")"
umask 077
BUCKET="kontrolia-sauvegardes"
REGION="rbx"
ENDPOINT="https://s3.rbx.io.cloud.ovh.net"

echo "1/4 Installation des outils (rclone, gpg)…"
command -v rclone >/dev/null || { apt-get update -qq && apt-get install -y -qq rclone; }
command -v gpg >/dev/null || apt-get install -y -qq gnupg

echo "2/4 Clés de l'utilisateur Object Storage (copiez-collez : rien ne s'affiche, c'est normal)"
read -rsp "  Clé d'accès (Access key) : " AK; echo
read -rsp "  Clé secrète (Secret key) : " SK; echo
# Copier-coller depuis un fichier : on retire espaces, guillemets, virgules et retours chariot éventuels
nettoyer() { printf '%s' "$1" | tr -d ' \t\r\n"'"'"',' ; }
AK="$(nettoyer "$AK")"; SK="$(nettoyer "$SK")"
[ -n "$AK" ] && [ -n "$SK" ] || { echo "Clé vide : rien n'est enregistré."; exit 1; }
if ! [[ "$AK" =~ ^[0-9a-f]{32}$ ]]; then
  echo "  La clé d'accès collée n'a pas le format OVH (32 caractères 0-9 et a-f) : ${#AK} caractères, commence par ${AK:0:4}…"
  echo "  Rien n'est enregistré. Copiez la clé d'accès dans OVH JUSTE AVANT de la coller ici, puis relancez."
  exit 1
fi
if [ ${#SK} -lt 20 ] || [[ "$SK" == *sudo* ]] || [[ "$SK" == */* ]] || [ "$SK" = "$AK" ]; then
  echo "  La clé secrète collée ne ressemble pas à une clé OVH (${#SK} caractères). Rien n'est enregistré."
  exit 1
fi
echo "  Clé d'accès : ${#AK} caractères, commence par ${AK:0:4}… ; clé secrète : ${#SK} caractères."
cat > sauvegarde_externe.env <<EOF
S3_BUCKET=$BUCKET
S3_REGION=$REGION
S3_ENDPOINT=$ENDPOINT
S3_ACCESS_KEY=$AK
S3_SECRET_KEY=$SK
EOF
chmod 600 sauvegarde_externe.env
unset AK SK

echo "3/4 Phrase secrète de chiffrement"
if [ -f .phrase_sauvegarde ]; then
  echo "  Phrase déjà présente : conservée (les anciennes copies restent lisibles)."
else
  openssl rand -base64 32 | tr -d '\n' > .phrase_sauvegarde
  chmod 600 .phrase_sauvegarde
  echo
  echo "  ┌─────────────────────────────────────────────────────────────────────┐"
  echo "  │ NOTEZ CETTE PHRASE SECRÈTE MAINTENANT (gestionnaire de mots de passe │"
  echo "  │ ou papier). Sans elle, les copies externes sont illisibles.         │"
  echo "  │ Ne la collez jamais dans une conversation.                           │"
  echo "  └─────────────────────────────────────────────────────────────────────┘"
  echo
  echo "     $(cat .phrase_sauvegarde)"
  echo
  read -rp "  Appuyez sur Entrée une fois la phrase notée… " _ < /dev/tty
  clear 2>/dev/null || true
fi

echo "4/4 Essai : sauvegarde, envoi chiffré et relecture"
./sauvegarde.sh
./restaurer_externe.sh
dernier="$(./restaurer_externe.sh | awk '{print $NF}' | grep 'smd_' | sort | tail -1)"
./restaurer_externe.sh "$dernier"
rm -f "sauvegardes/restauree_${dernier%.gpg}"
echo "✅ Copie externe opérationnelle : chaque nuit, la sauvegarde est envoyée chiffrée vers $BUCKET ($REGION)."
