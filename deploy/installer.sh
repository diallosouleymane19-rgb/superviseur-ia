#!/usr/bin/env bash
# Superviseur IA Comptable — installation sur un serveur OVH neuf (Ubuntu 24.04).
# À lancer avec sudo depuis le dossier du projet :  sudo bash /opt/superviseur/deploy/installer.sh
# Peut être relancé sans risque : ce qui est déjà fait est conservé (mots de passe, données).
set -euo pipefail

DOSSIER="$(cd "$(dirname "$0")" && pwd)"
cd "$DOSSIER"
etape() { echo; echo "━━━ $* ━━━"; }
erreur() { echo "❌ $*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || erreur "Lancez la commande avec sudo."
. /etc/os-release
[ "${ID:-}" = "ubuntu" ] || erreur "Ce script est prévu pour Ubuntu (trouvé : ${PRETTY_NAME:-inconnu})."

etape "1/7 Mise à jour du système et installation des outils"
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get upgrade -yq
apt-get install -yq docker.io docker-compose-v2 ufw fail2ban unattended-upgrades nano curl git openssl
systemctl enable --now docker
systemctl enable --now fail2ban
dpkg-reconfigure -f noninteractive unattended-upgrades   # correctifs de sécurité automatiques

etape "2/7 Pare-feu : seuls SSH, HTTP et HTTPS sont ouverts"
ufw allow OpenSSH > /dev/null
ufw allow 80/tcp > /dev/null
ufw allow 443 > /dev/null
ufw --force enable > /dev/null
ufw status | sed -n '1,12p'

etape "3/7 Adresse de l'application"
if [ ! -f .env ]; then
  read -r -p "Adresse de l'application [app.smdconsulting.pro] : " DOMAINE < /dev/tty
  DOMAINE="${DOMAINE:-app.smdconsulting.pro}"
  read -r -p "E-mail pour le certificat HTTPS (alertes d'expiration) : " EMAIL_CERTIFICAT < /dev/tty
  [ -n "$EMAIL_CERTIFICAT" ] || erreur "E-mail obligatoire."
  umask 077
  {
    echo "DOMAINE=$DOMAINE"
    echo "EMAIL_CERTIFICAT=$EMAIL_CERTIFICAT"
    echo "POSTGRES_PASSWORD=$(openssl rand -hex 24)"
  } > .env
  umask 022
  echo "✅ Paramètres enregistrés dans $DOSSIER/.env (mot de passe de la base généré au hasard)."
else
  echo "✅ Paramètres déjà présents ($DOSSIER/.env) : conservés."
fi
DOMAINE="$(grep '^DOMAINE=' .env | cut -d= -f2)"

etape "4/7 Clés secrètes de l'application"
if [ ! -f secrets.toml ]; then
  umask 077
  cat > secrets.toml <<'MODELE'
# Collez ici le contenu des « Secrets » de Streamlit Cloud
# (share.streamlit.io → votre application → Settings → Secrets), à la place de cette ligne.
# Enregistrer : Ctrl+O puis Entrée.  Quitter : Ctrl+X.
MODELE
  umask 022
  echo "L'éditeur va s'ouvrir : collez vos secrets Streamlit (clic droit dans le terminal), puis Ctrl+O, Entrée, Ctrl+X."
  read -r -p "Appuyez sur Entrée pour ouvrir l'éditeur… " _ < /dev/tty
  nano secrets.toml < /dev/tty > /dev/tty
fi
grep -q '^MISTRAL_API_KEY' secrets.toml || erreur "MISTRAL_API_KEY absent de secrets.toml : relancez le script après l'avoir ajouté (sudo nano $DOSSIER/secrets.toml)."
# Adresse publique utilisée pour les retours de paiement Stripe
if grep -q '^APP_URL' secrets.toml; then
  sed -i "s#^APP_URL.*#APP_URL = \"https://$DOMAINE\"#" secrets.toml
else
  echo "APP_URL = \"https://$DOMAINE\"" >> secrets.toml
fi
chown 1000 secrets.toml && chmod 600 secrets.toml   # lisible par l'application seule
echo "✅ secrets.toml prêt (droits restreints)."

etape "5/7 Construction et démarrage (5 à 10 minutes la première fois)"
docker compose up -d --build

etape "6/7 Sauvegarde automatique de la base chaque nuit à 2 h 30"
chmod +x sauvegarde.sh mettre_a_jour.sh
cat > /etc/cron.d/superviseur-sauvegarde <<CRON
30 2 * * * root $DOSSIER/sauvegarde.sh >> /var/log/superviseur-sauvegarde.log 2>&1
CRON
echo "✅ Planifiée (journal : /var/log/superviseur-sauvegarde.log)."

etape "7/7 Vérifications"
for i in $(seq 1 30); do
  etat="$(docker inspect -f '{{.State.Health.Status}}' "$(docker compose ps -q app)" 2>/dev/null || true)"
  [ "$etat" = "healthy" ] && break
  sleep 5
done
docker compose ps
[ "$etat" = "healthy" ] && echo "✅ Application démarrée." || erreur "L'application ne répond pas : envoyez la sortie de « sudo docker compose -f $DOSSIER/docker-compose.yml logs app --tail 50 »."

IP="$(curl -4 -fsS https://api.ipify.org 2>/dev/null || hostname -I | cut -d' ' -f1)"
DNS="$(getent ahostsv4 "$DOMAINE" | awk 'NR==1{print $1}' || true)"
if [ "$DNS" = "$IP" ]; then
  echo "✅ $DOMAINE pointe bien vers ce serveur ($IP)."
  if curl -fsS --max-time 20 "https://$DOMAINE/_stcore/health" > /dev/null 2>&1; then
    echo "✅ HTTPS actif : ouvrez https://$DOMAINE"
  else
    echo "⏳ Certificat HTTPS en cours d'obtention : réessayez https://$DOMAINE dans 2 minutes."
  fi
else
  echo "⚠️  $DOMAINE ne pointe pas encore vers ce serveur."
  echo "    Dans OVH → Zones DNS → smdconsulting.pro, ajoutez un enregistrement A : ${DOMAINE%%.*} → $IP"
  echo "    Le certificat HTTPS sera obtenu automatiquement dès que le DNS sera à jour."
fi
