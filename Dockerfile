# ── ForexAI — FastAPI API + SignalScheduler (and the trade monitor) ──────────
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Minimal build tools in case a transitive dep lacks a wheel
RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# Pinned, complete lockfile (generated from the working venv)
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# App code + runner scripts only (secrets/.env are injected at runtime, see compose)
COPY app ./app
COPY init_db.py run_monitor.py backtest.py ./

EXPOSE 8000

# Default service = API + auto-started scheduler (alerts + paper trades).
# The monitor service overrides this command in docker-compose.yml.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
