#!/usr/bin/env bash
set -euo pipefail

DEPLOY_USER="${DEPLOY_USER:-deploy}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root on a fresh Ubuntu server." >&2
  exit 1
fi

if ! id "${DEPLOY_USER}" >/dev/null 2>&1; then
  adduser --disabled-password --gecos "" "${DEPLOY_USER}"
fi

usermod -aG sudo "${DEPLOY_USER}"

apt-get update
apt-get install -y ca-certificates curl fail2ban git ufw

ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

usermod -aG docker "${DEPLOY_USER}"

echo "Bootstrap complete. Add your SSH key for ${DEPLOY_USER}, then reconnect as that user."
