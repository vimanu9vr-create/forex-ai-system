# 🤖 Forex AI System — Multi-Agent Autonomous Trading Platform

[![CI Pipeline](https://github.com/vimanu9vr-create/forex-ai-system/actions/workflows/ci.yml/badge.svg)](https://github.com/vimanu9vr-create/forex-ai-system/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![CrewAI](https://img.shields.io/badge/CrewAI-Multi--Agent-orange)](https://crewai.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-Dashboard-61DAFB?logo=react)](https://react.dev)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> A production-grade, 5-agent autonomous forex analysis and paper-trading platform built with **CrewAI**, **Python**, **FastAPI**, and **React**. Features institutional Smart Money Concepts (SMC) analysis, walk-forward backtesting, real-time Telegram alerts, and a live dashboard.

⚠️ **Research & paper-trading only. Not financial advice. Does not place real broker orders.**

---

## 📋 Table of Contents

- [Architecture](#-architecture)
- [Agent System](#-agent-system)
- [Features](#-features)
- [Backtesting Results](#-backtesting-results)
- [Quick Start](#-quick-start)
- [Configuration](#️-configuration)
- [Project Structure](#-project-structure)
- [Running Tests](#-running-tests)
- [Tech Stack](#-tech-stack)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR AGENT                          │
│              (Coordinates all agents & workflow)                │
└──────────────┬──────────────────────────────┬───────────────────┘
               │                              │
    ┌──────────▼──────────┐      ┌───────────▼────────────┐
    │    MARKET AGENT     │      │   RISK MANAGER AGENT   │
    │  Polygon (primary)  │      │  Position sizing       │
    │  TwelveData (fallbk)│      │  Stop loss calculation │
    │  SMC Analysis       │      │  R:R validation (≥3.0) │
    │  Volume Profile     │      │  Macro event-risk gate │
    │  Wyckoff phases     │      └───────────┬────────────┘
    └──────────┬──────────┘                  │
               │                  ┌──────────▼──────────┐
               └──────────────────▶  EXECUTION AGENT   │
                                  │  Paper trade logger │
                                  │  SQLite persistence │
                                  │  Telegram alerts    │
                                  └──────────┬──────────┘
                                             │
                                  ┌──────────▼──────────┐
                                  │  REFLECTION AGENT   │
                                  │  Post-trade eval    │
                                  │  Self-improvement   │
                                  │  Strategy feedback  │
                                  └─────────────────────┘
                                             │
                                  ┌──────────▼──────────┐
                                  │   React Dashboard   │
                                  │   Live signals      │
                                  │   Trade history     │
                                  └─────────────────────┘
```

---

## 🤖 Agent System

| Agent | Role | Tools Used |
|-------|------|-----------|
| 🧠 **Orchestrator** | Coordinates all agents, manages workflow | CrewAI Hierarchical Process |
| 📊 **Market Agent** | SMC analysis, Volume Profile, Wyckoff | Polygon API, TwelveData API |
| ⚠️ **Risk Manager** | Position sizing, stop loss, R:R validation | Finnhub Calendar, Custom Risk Engine |
| ⚡ **Execution Agent** | Paper trade placement, Telegram alerts | SQLite, Telegram Bot API |
| 🔄 **Reflection Agent** | Post-trade evaluation, strategy improvement | Trade history, Performance metrics |

---

## ✨ Features

- **5-Agent CrewAI Architecture** — Orchestrator, Market, Risk Manager, Execution, Reflection
- **Institutional SMC Analysis** — BOS, CHoCH, FVG, Order Blocks, Liquidity Sweeps
- **Volume Profile** — Real tick-volume from Polygon (POC, Value Area)
- **Wyckoff Analysis** — Accumulation/distribution phases, springs, upthrusts
- **Walk-Forward Backtesting** — No-lookahead, cost-modeled, out-of-sample validated
- **Multi-Data Feeds** — Polygon (primary) + TwelveData (fallback)
- **Macro Event Gating** — Finnhub economic calendar (avoids NFP, FOMC etc.)
- **Real-Time Alerts** — Telegram bot integration
- **Live Dashboard** — React + Vite frontend with FastAPI backend
- **Docker Ready** — One-command deployment with docker-compose
- **Honest Backtesting** — Reports losses too, not just wins

---

## 📊 Backtesting Results

> Walk-forward, no-lookahead, conservative fills, 1.5-pip spread modeled per trade

| Timeframe | Result | Verdict |
|-----------|--------|---------|
| **Daily (GBPUSD/EURUSD)** | **+0.26R/trade, PF 1.5–1.9** | ✅ Survives costs |
| 1h | −0.03R/trade | ❌ Loses after costs |
| 4h | −0.13R/trade | ❌ Negative even gross |
| 15m | −0.63R gross | ❌ Broken |
| 5m (scalping) | −1.0R gross, 0% win | ❌ Dead |

**Out-of-sample validation:** GBPUSD Daily held — +0.57R (train) → **+0.65R, PF 1.92 (unseen)**

> ⚠️ Small sample (~20–50 trades). Forward-test on demo before trusting.

---

## 🚀 Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/vimanu9vr-create/forex-ai-system.git
cd forex-ai-system
cp .env.example app/.env   # Add your API keys
docker compose up -d --build
```

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:8080 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

```bash
docker compose logs -f    # Watch logs
docker compose down       # Stop (data persists)
```

### Manual / Development

```bash
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python init_db.py
uvicorn app.main:app --reload --port 8000   # API + scheduler
python run_monitor.py                        # Trade monitor (separate shell)
cd frontend && npm install && npm run dev    # Dashboard at :5173
```

---

## ⚙️ Configuration

Copy `.env.example` to `app/.env` and fill in your keys:

```env
# Market Data
POLYGON_API_KEY=          # Primary feed (real tick-volume)
TWELVEDATA_API_KEY=       # Fallback feed + historical data
FINNHUB_API_KEY=          # Macro calendar + news

# AI (CrewAI uses OpenAI)
OPENAI_API_KEY=

# Telegram Alerts
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Strategy (validated edge only)
STRATEGY_PAIRS=GBPUSD,EURUSD
STRATEGY_TIMEFRAME=1day
MIN_RISK_REWARD=3.0
SCAN_INTERVAL_SECONDS=3600

# Auth & DB
AUTH_USERNAME=admin
AUTH_PASSWORD=change_me
DATABASE_URL=sqlite:///./forex_ai.db
```

---

## 📁 Project Structure

```
forex-ai-system/
├── .github/
│   └── workflows/
│       └── ci.yml              # CI/CD pipeline
├── app/
│   ├── agents/
│   │   └── market_agent.py     # Multi-TF SMC analysis
│   ├── crew/                   # CrewAI desk analyst agent
│   ├── routes/                 # FastAPI endpoints
│   ├── services/
│   │   ├── market_data.py      # Polygon + TwelveData feeds
│   │   ├── macro_service.py    # Finnhub calendar
│   │   ├── signal_scheduler.py # Hourly signal scanner
│   │   └── telegram_service.py # Alert delivery
│   └── smart_money/
│       ├── live_pair_scanner.py   # Stacked-MA trend engine
│       ├── risk_management.py     # Trade levels + 1:3 R:R
│       ├── market_profile.py      # Volume Profile / TPO
│       ├── wyckoff.py             # Wyckoff phase detection
│       └── backtester.py          # Walk-forward backtester
├── frontend/                   # React + Vite dashboard
├── tests/                      # Test suite
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🧪 Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/test_intraday_engine.py -v
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **AI Agents** | CrewAI, OpenAI GPT-4 |
| **Backend** | Python 3.11, FastAPI, SQLite |
| **Frontend** | React, Vite, TypeScript |
| **Data Feeds** | Polygon, TwelveData, Finnhub |
| **Alerts** | Telegram Bot API |
| **DevOps** | Docker, docker-compose, GitHub Actions |
| **Testing** | pytest, pytest-asyncio, pytest-cov |

---

## ⚠️ Disclaimer

This is a research and education project. Not financial advice. No warranty. Past or backtested performance does not predict future results. You are responsible for your own trading decisions and for complying with the laws and regulations of your jurisdiction.

---

## 👨‍💻 Author

**Vignesh A** — AI Engineer · Multi-Agent Systems · CrewAI Specialist

[![Email](https://img.shields.io/badge/Email-Vimanu9.vr%40gmail.com-red?logo=gmail)](mailto:Vimanu9.vr@gmail.com)
[![GitHub](https://img.shields.io/badge/GitHub-vimanu9vr--create-black?logo=github)](https://github.com/vimanu9vr-create)

---

*Certified in Agentic AI, Generative AI for Everyone, and AI Prompting for Everyone by DeepLearning.AI (Andrew Ng)*
