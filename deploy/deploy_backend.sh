#!/usr/bin/env bash
# Deploys a new backend version on the EC2 server. Called by the GitHub
# Actions deploy workflow over SSH, or by hand:
#   bash /opt/member-portal/deploy/deploy_backend.sh [git-ref]
set -euo pipefail

GIT_REF="${1:-origin/main}"
APP_DIR=/opt/member-portal

cd "$APP_DIR"
PREVIOUS_REF="$(git rev-parse HEAD)"
echo "==> Currently deployed: $PREVIOUS_REF"

echo "==> Fetching and checking out $GIT_REF"
git fetch --all --prune
git checkout --detach "$GIT_REF"

echo "==> Installing Python dependencies"
"$APP_DIR/venv/bin/pip" install --quiet -r backend/requirements.txt

echo "==> Restarting the service"
sudo /usr/bin/systemctl restart member-portal

echo "==> Waiting for the health check"
for attempt in $(seq 1 15); do
  if curl --silent --fail http://127.0.0.1:8000/api/v1/health >/dev/null; then
    echo "==> Deployed $(git rev-parse --short HEAD); health check passed."
    exit 0
  fi
  sleep 2
done

# The new version did not come up: go back to the version that was running.
echo "!! Health check failed. Rolling back to $PREVIOUS_REF" >&2
git checkout --detach "$PREVIOUS_REF"
"$APP_DIR/venv/bin/pip" install --quiet -r backend/requirements.txt
sudo /usr/bin/systemctl restart member-portal
exit 1
