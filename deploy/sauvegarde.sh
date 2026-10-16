#!/usr/bin/env bash
# Sauvegarde de la base PostgreSQL (lancée chaque nuit par cron, installée par installer.sh).
# Fichiers compressés dans deploy/sauvegardes/, gardés 14 jours, lisibles par l'administrateur seul.
set -euo pipefail
cd "$(dirname "$0")"
umask 077
mkdir -p sauvegardes
fichier="sauvegardes/smd_$(date +%Y-%m-%d_%H%M).sql.gz"
docker compose exec -T db pg_dump -U smd -d smd --no-owner | gzip > "$fichier.tmp"
# Une sauvegarde vide ou tronquée n'écrase rien
if [ "$(gzip -cd "$fichier.tmp" | grep -c 'CREATE TABLE')" -lt 9 ]; then
  echo "$(date '+%F %T') ÉCHEC : sauvegarde incomplète" >&2
  rm -f "$fichier.tmp"
  exit 1
fi
mv "$fichier.tmp" "$fichier"
find sauvegardes -name 'smd_*.sql.gz' -mtime +14 -delete
echo "$(date '+%F %T') OK : $fichier ($(du -h "$fichier" | cut -f1))"
# Copie chiffrée hors du serveur (si configurée) ; un échec ici n'annule pas la sauvegarde locale
./sauvegarde_externe.sh || echo "$(date '+%F %T') ÉCHEC copie externe (la sauvegarde locale est faite)" >&2
