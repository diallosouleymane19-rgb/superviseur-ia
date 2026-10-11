#!/usr/bin/env bash
# Met l'application à jour avec la dernière version publiée sur GitHub (sauvegarde de la base avant).
set -euo pipefail
cd "$(dirname "$0")"
./sauvegarde.sh
git -C .. pull --ff-only
docker compose up -d --build
docker image prune -f > /dev/null
docker compose ps
