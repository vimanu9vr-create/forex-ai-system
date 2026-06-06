# ForexAI — Institutional Trading Frontend

Production-ready React + TypeScript dashboard for the ForexAI FastAPI backend.

## Quick Start

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on **http://localhost:3000**  
Backend must be running on **http://127.0.0.1:8000**

## Features

- **Dashboard** — Live KPI cards, TradingView chart, risk monitor, scheduler control
- **Live Signals** — Real-time signals via WebSocket + HTTP polling every 10s, execute trades directly
- **Analytics** — Charts: pair performance, buy/sell split, open/closed distribution
- **Trade History** — Searchable table, trade detail popup, CSV export
- **AI Analysis** — BOS, CHOCH, liquidity sweeps, session analysis, CrewAI probability
- **Settings** — OANDA API key, Telegram bot config, risk management sliders

## Env Variables

Copy `.env` and adjust if needed:

```
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_WS_URL=ws://127.0.0.1:8000
```

## Build for Production

```bash
npm run build
# Output: dist/
```
