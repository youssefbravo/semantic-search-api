# Deployment Runbook

Human-required prerequisite: create the server yourself. Do not store production secrets in the repo.

Recommended box: Hetzner CX22, Ubuntu LTS, Berlin/Nuremberg region. AWS EC2 `t3.small` is also fine if you prefer AWS vocabulary.

## 1. Create Server

Minimum:

- Ubuntu 24.04 LTS
- 2 vCPU / 4 GB RAM
- SSH key login
- Public IPv4

Record:

- Server IP
- SSH username
- Domain or subdomain for the API/frontend

## 2. Harden Linux

Run as root once:

```bash
adduser deploy
usermod -aG sudo deploy
rsync --archive --chown=deploy:deploy ~/.ssh /home/deploy
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
apt update
apt install -y fail2ban git ca-certificates curl
```

Then reconnect as `deploy`.

## 3. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker deploy
```

Log out and back in, then verify:

```bash
docker version
docker compose version
```

## 4. Clone And Configure

```bash
git clone https://github.com/youssefbravo/semantic-search-api.git
cd semantic-search-api
cp .env.example .env
```

Edit `.env` on the server only. Use production passwords. Never commit `.env`.

## 5. Start The Stack

```bash
docker compose up -d --build
docker compose exec api python -m eval.ingest_corpus --reset
curl http://localhost:8000/health
```

Expected local health response today:

```json
{"status":"ok","checks":{"postgres":true,"redis":true}}
```

`/health` checks Postgres and Redis, not just process liveness.

## 6. HTTPS Reverse Proxy

Use Caddy for automatic Let's Encrypt certificates.

Example `/etc/caddy/Caddyfile`:

```caddyfile
api.example.com {
    reverse_proxy localhost:8000
}

search.example.com {
    reverse_proxy localhost:3000
}
```

Then:

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

## 7. Deployment Smoke Test

```bash
curl https://api.example.com/health
curl https://api.example.com/docs
```

Then run one search from the frontend and one direct API request.

## 8. CI/CD Sketch

After the server is reachable, add GitHub Actions repository secrets:

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_SSH_KEY`
- `DEPLOY_PATH`

Deployment job shape:

```bash
ssh deploy@$DEPLOY_HOST "cd $DEPLOY_PATH && git pull && docker compose up -d --build"
```

Do this only after the `CI` workflow is green on `main`.

## 9. Monitoring Plan

Minimum public proof:

- UptimeRobot ping for `/health`
- Grafana screenshot showing request rate, p95 latency, error rate, and Celery queue depth

Implemented locally:

- `/metrics` is exposed by FastAPI when `METRICS_ENABLED=true`.
- Prometheus runs on `:9090` and scrapes `api:8000/metrics`.
- Grafana runs on `:3001` with default local credentials `admin` / `admin`.
- Grafana provisions the `Semantic Search API` dashboard automatically.

Start monitoring locally with:

```bash
docker compose --profile monitoring up -d prometheus grafana
```

Production TODOs:

- Change the Grafana admin password before exposing it.
- Put Grafana behind Caddy/auth or keep it private over SSH tunnel/VPN.
- Add Celery queue-depth metrics (`LLEN celery`) for queue visibility.
- Capture a dashboard screenshot for the README after deployment.

## 10. Public Guardrails

Before public launch:

- Keep rate limiting enabled.
- Keep upload cap enabled.
- Set `INGEST_API_KEY` so `POST /documents` requires `X-API-Key`.
- Use production database/Redis passwords.
- Confirm `gitleaks detect` still reports no leaks.
