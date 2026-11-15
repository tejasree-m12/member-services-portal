#!/usr/bin/env bash
# One-time setup of a fresh Ubuntu 24.04 EC2 instance.
# Run as the default "ubuntu" user:  bash ec2_setup.sh <git-repository-url>
# Read docs/DEPLOYMENT.md first; this script is the commands from that guide.
set -euo pipefail

REPO_URL="${1:?Usage: bash ec2_setup.sh <git-repository-url>}"
APP_DIR=/opt/member-portal

echo "==> Installing system packages"
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip git nginx mysql-server

echo "==> Creating the application user and folder"
# A dedicated user with no login shell: if the app is ever compromised, the
# attacker does not get an account that can administer the server.
id portal >/dev/null 2>&1 || sudo useradd --system --create-home --shell /usr/sbin/nologin portal
sudo mkdir -p "$APP_DIR"
sudo chown "$USER":portal "$APP_DIR"
[ -d "$APP_DIR/.git" ] || git clone "$REPO_URL" "$APP_DIR"

echo "==> Creating the Python virtual environment"
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt"

echo "==> Installing the nginx site and the systemd service"
sudo cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/member-portal
sudo ln -sf /etc/nginx/sites-available/member-portal /etc/nginx/sites-enabled/member-portal
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
sudo cp "$APP_DIR/deploy/member-portal.service" /etc/systemd/system/member-portal.service
sudo systemctl daemon-reload
sudo systemctl enable member-portal

# Let the deploy script restart the service without a password prompt.
echo "$USER ALL=(root) NOPASSWD: /usr/bin/systemctl restart member-portal" \
  | sudo tee /etc/sudoers.d/member-portal-deploy >/dev/null
sudo chmod 440 /etc/sudoers.d/member-portal-deploy

cat <<'NEXT'

Setup finished. Still to do by hand (see docs/DEPLOYMENT.md, steps 4 to 6):
  1. Create the MySQL database and user.
  2. Create /opt/member-portal/backend/.env with real secrets (chmod 640, group portal).
  3. Create the tables and the first admin account:
       cd /opt/member-portal/backend
       ../venv/bin/flask --app wsgi init-db
       ../venv/bin/flask --app wsgi create-admin
  4. sudo systemctl start member-portal
NEXT
