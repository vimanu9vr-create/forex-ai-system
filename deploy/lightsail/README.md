# Run forex-ai 24/7 on AWS Lightsail

The pragmatic way to keep the bot alive so it never misses a London/NY killzone — a single
small VM running the existing `docker-compose` stack. Far simpler than ECS Fargate, ~$10–12/mo.

## 1. Create the instance (AWS Console)
1. **Lightsail → Create instance**
2. Platform **Linux/Unix**, blueprint **OS Only → Ubuntu 24.04 LTS**
3. Plan: **2 GB RAM** (~$12/mo). *1 GB works but the first build is tight even with swap — 2 GB is safer.*
4. Name it `forex-ai`, **Create instance**.

## 2. Open the dashboard port (only if you want the web UI)
Instance → **Networking** tab → **IPv4 Firewall → Add rule** → **Custom / TCP / 8080**.
(Skip this if you only care about Telegram alerts — the bot needs no inbound ports for those.)
Consider restricting the source to your IP. Optionally also open **8000** for the API.

## 3. Deploy
Instance → **Connect using SSH** (browser terminal), then:

```bash
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/vimanu9vr-create/forex-ai-system.git
cd forex-ai-system
git checkout feature/langgraph-aws   # all the latest fixes live here until the PR is merged to main
bash deploy/lightsail/setup.sh
```

> Once you merge the `feature/langgraph-aws` PR into `main`, drop the `git checkout` line and
> just deploy from `main`. (Right now `main` is the old pre-fix code — do **not** deploy it.)

The script installs Docker + swap, then writes a template `app/.env` and stops. Fill in your keys:

```bash
nano app/.env      # POLYGON_API_KEY, OPENAI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ...
bash deploy/lightsail/setup.sh     # re-run — now it builds + starts everything
```

(Or copy your working local file up instead of retyping keys:
`scp -i <key.pem> app/.env ubuntu@<instance-ip>:~/forex-ai-system/app/.env`)

## 4. Verify
```bash
sudo docker compose ps            # app / monitor / dashboard = Up
sudo docker compose logs -f app   # watch scans + "[IntradayAlerts]" during killzones
```
- Dashboard: `http://<instance-ip>:8080`
- It **auto-restarts** (compose `restart: unless-stopped` + Docker enabled on boot), so a reboot or crash self-heals — the uptime fix.

## Updating later
```bash
cd ~/forex-ai-system && git pull && sudo docker compose up -d --build
```

## Cost control
Stop the instance from the Lightsail console when you don't need it (you still pay for the
plan while it exists; **delete** it to stop billing entirely).
