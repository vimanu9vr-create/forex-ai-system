#!/usr/bin/env bash
# One-shot setup for the forex-ai stack on an Ubuntu (22.04/24.04) AWS Lightsail instance.
# Keeps the bot running 24/7 so killzone signals are never missed.
#
# Run it FROM the cloned repo on the instance:
#   sudo apt-get update && sudo apt-get install -y git
#   git clone https://github.com/vimanu9vr-create/forex-ai-system.git
#   cd forex-ai-system && bash deploy/lightsail/setup.sh
#
# Idempotent: safe to re-run (e.g. after editing app/.env or pulling new code).
set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
echo "== forex-ai Lightsail setup =="

# 1) Swap — pip installing crewai/langchain/langgraph + the vite build can OOM on 1–2GB RAM.
if ! sudo swapon --show | grep -q .; then
  echo "-> adding 2G swap"
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

# 2) Docker + compose plugin (start on boot).
if ! command -v docker >/dev/null 2>&1; then
  echo "-> installing Docker"
  curl -fsSL https://get.docker.com | sudo sh
fi
sudo systemctl enable --now docker

# 3) Secrets. app/.env is gitignored, so a fresh clone won't have it — create a template
#    on first run and stop so you can fill in your keys.
if [ ! -f app/.env ]; then
  echo "-> app/.env not found — writing a template"
  cat > app/.env <<'ENV'
# ── Required ──────────────────────────────────────────────
POLYGON_API_KEY=
TWELVEDATA_API_KEY=
OPENAI_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
# ── Optional ──────────────────────────────────────────────
FINNHUB_API_KEY=
LLM_PROVIDER=openai
# AWS (S3 backups / Bedrock) — leave blank if unused
AWS_S3_BUCKET=
AWS_REGION=
ENV
  echo ""
  echo ">>> Edit app/.env with your keys:   nano app/.env"
  echo ">>> Then re-run:                    bash deploy/lightsail/setup.sh"
  exit 0
fi

# 4) Build + start (restart:unless-stopped in the compose file keeps it alive across reboots).
echo "-> building + starting the stack (first build takes a few minutes)"
sudo docker compose up -d --build

echo ""
echo "== done =="
IP=$(curl -fsS -m 5 https://checkip.amazonaws.com 2>/dev/null || echo "<instance-ip>")
echo "Dashboard : http://$IP:8080   (open port 8080 in the Lightsail 'Networking' tab)"
echo "API/health: http://$IP:8000/openapi.json"
echo "Logs      : sudo docker compose logs -f app"
echo "Telegram alerts fire automatically during the London/NY killzones."
