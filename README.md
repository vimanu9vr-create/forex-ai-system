# Forex AI — Institutional SMC Analysis & Paper-Trading System

A multi-method forex **analysis and paper-trading research platform**. It scans the
market with a disciplined Smart-Money engine, produces institutional-style desk
analysis via a CrewAI agent, **paper-trades** the one strategy that survived honest
backtesting, and ships as a one-command Docker stack with a live dashboard and
Telegram alerts.

> ⚠️ **Read this first — honest disclaimer**
> This is a **research / paper-trading** tool, **not** financial advice and **not** a
> proven money-maker. It does **not** place real broker orders. Backtesting found a
> *narrow, modest* edge on **GBPUSD/EURUSD daily** that survives costs — and found that
> lower timeframes (1h, 15m, scalping) **lose money after spread**. Treat any signal as a
> candidate to **forward-test on demo**, not a guarantee. Trading forex carries real risk;
> check what's legal in your jurisdiction before risking capital.

---

## What makes this different

Most "AI forex bot" repos sell a fantasy. This one is **honest about its own results**:

- It was **backtested, cost-modeled, and out-of-sample validated** — and the README reports
  what that actually showed, including where it *loses*.
- The "score" is labeled **`confluence_score`** (a checklist), not "probability" — because
  testing showed the score **does not reliably predict wins**.
- When there's no quality setup, it returns **NO-TRADE** instead of inventing one. When a
  data dimension is missing, the analyst writes *"pending data integration"* instead of
  fabricating numbers.

---

## Honest results (what the backtester found)

Engine: stacked-MA trend filter + structure-based entries, 1:3 R:R, walk-forward, no
lookahead, conservative fills. Spread modeled as a per-trade cost.

| Timeframe | Net of ~1.5-pip cost | Verdict |
|---|---|---|
| **Daily (GBPUSD/EURUSD)** | **+0.26R/trade**, PF 1.5–1.9 | ✅ survives costs |
| 1h | −0.03R/trade | ❌ loses after costs |
| 4h | −0.13R/trade | ❌ negative even gross |
| 15m | −0.63R gross | ❌ broken |
| 5m (scalping) | −1.0R gross, 0% win | ❌ dead |

**Out-of-sample (train on old half, test on unseen half), net of costs:**
GBPUSD daily held up — +0.57R (train) → **+0.65R, PF 1.92 (unseen)**. EURUSD was
inconsistent (old half negative). Samples are small (~20–50 trades/pair), so this is a
**promising candidate to forward-test, not a proven system.**

**Bottom line:** the only configuration worth paper-trading is **GBPUSD/EURUSD on the Daily
timeframe** — which is exactly what the live engine is configured to run.

---

## How it works

```
Polygon (primary, real tick-volume) ─┐
TwelveData (fallback, OHLC) ──────────┼─▶  SMC engine ──▶ live_pair_scanner ──▶ trade_levels
Finnhub (economic calendar + news) ──┘        │                 │                    │
                                              ▼                 ▼                    ▼
                                     Volume Profile,     stacked-MA trend     structure entry,
                                     Wyckoff, macro       (pullback-robust)   1:3, invalidation,
                                     event-risk gate                          TP1/TP2/TP3 plan
                                              │
        ┌─────────────────────────────────────┴───────────────────────────────────┐
        ▼                                                                           ▼
  SignalScheduler (hourly)                                              CrewAI desk analyst
  → Telegram alert + paper trade                                        → full ICT/SMC/Wyckoff/
  for each NEW GBPUSD/EURUSD daily setup                                  Volume/Macro write-up +
                                                                         "would I risk my own capital?"
        │                                                                           │
        ▼                                                                           ▼
  SQLite (trades)  ◀── trade monitor closes at TP/SL ──▶  React dashboard + Telegram
```

### The disciplined engine
- **Direction:** stacked moving-average trend (MA20 > MA50 > MA100 + slope). Robust to
  pullbacks — it buys dips in an uptrend instead of flipping on every retrace.
- **Entry:** only when price is in the *discount* half of the range for longs (premium for
  shorts) — never chases the top/bottom.
- **Stops/targets:** structure-based (beyond the swing); target = opposing range liquidity;
  rejected unless R:R ≥ `MIN_RISK_REWARD` (default **3.0**).
- **Plan:** every signal carries an **invalidation level** + a **TP1 (1R, move to BE) / TP2
  (2R, trail) / TP3 (target)** management plan.

### Multi-method analysis (CrewAI)
The `/crew-analysis` agent reasons like a desk analyst, combining: higher-timeframe trend,
liquidity sweep (where retail is trapped), BOS/CHoCH, FVG/OB entry, **Volume Profile**
(POC/value area — real tick-volume from Polygon, or time-based TPO otherwise), **Wyckoff**
phase (accumulation/distribution, springs/upthrusts), and **macro** event-risk
(Finnhub economic calendar — e.g. it stands aside before NFP). It ends with
*"Would I take this trade with my own capital? Why or why not?"* — and never fabricates data.

---

## Quick start (Docker — recommended)

```bash
git clone <your-repo> && cd forex-ai-system
cp .env.example app/.env          # then fill in your keys (see below)
docker compose up -d --build
```

| Service | URL / role |
|---|---|
| Dashboard | http://localhost:8080 |
| API | http://localhost:8000 (also proxied at `:8080/api`) |
| Scheduler | scans GBPUSD/EURUSD daily, Telegram alerts + paper trades |
| Monitor | closes paper trades at TP/SL |

```bash
docker compose logs -f      # watch ("No valid setup — NO-TRADE" is healthy)
docker compose ps           # all three Up
docker compose down         # stop (data persists in the volume)
```

> Run it on an **always-on host** (a small VPS) so the scheduler is alive at the daily
> close (~22:00 UTC). A laptop that sleeps will miss signals.

## Manual / dev setup

```bash
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python init_db.py
uvicorn app.main:app --reload --port 8000     # API + scheduler
python run_monitor.py                          # (separate shell) trade monitor
cd frontend && npm install && npm run dev       # dashboard at :5173
```

---

## Configuration

Keys live in `app/.env` (gitignored). In Docker they're injected via `env_file`.

```env
# ── Market data ───────────────────────────────────────────
POLYGON_API_KEY=          # primary feed — real forex tick-volume
TWELVEDATA_API_KEY=       # fallback feed + deepest 1h/daily history for backtests
FINNHUB_API_KEY=          # macro: economic calendar + market news

# ── CrewAI desk analyst (uses OpenAI) ─────────────────────
OPENAI_API_KEY=

# ── Telegram alerts ───────────────────────────────────────
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# ── Strategy (the validated edge) ─────────────────────────
STRATEGY_PAIRS=GBPUSD,EURUSD     # what the live engine trades
STRATEGY_TIMEFRAME=1day          # the only TF that survived costs
SCAN_INTERVAL_SECONDS=3600
MIN_RISK_REWARD=3.0

# ── Auth / DB ─────────────────────────────────────────────
AUTH_USERNAME=admin
AUTH_PASSWORD=change_me
DATABASE_URL=sqlite:///./forex_ai.db
```

---

## Backtesting

```bash
python backtest.py                  # all pairs, 1h, with per-confluence buckets
python backtest.py GBPUSD 1day      # single pair / timeframe
```
The backtester (`app/smart_money/backtester.py`) is walk-forward and **no-lookahead**:
a setup is detected at a bar's close and the outcome simulated forward (SL-first =
conservative). `backtest_all(interval=..., cost_pips=...)` supports cost modeling, and
results bucket win-rate by `confluence_score`.

---

## Project structure (key parts)

```
app/
  smart_money/
    live_pair_scanner.py   # stacked-MA trend, scans STRATEGY_PAIRS/TIMEFRAME
    risk_management.py     # trade_levels: structure entries, 1:3, invalidation, TP1/2/3
    market_profile.py      # Volume Profile (real volume) / TPO (time-at-price)
    wyckoff.py             # accumulation/distribution phase, spring/upthrust
    backtester.py          # walk-forward + cost modeling + OOS
    {structure,bos,choch,sweeps,liquidity,fvg,order_blocks,killzones,bias,probability_engine}.py
  services/
    market_data.py         # Polygon-first feed w/ throttle + TwelveData fallback + cache
    polygon_service.py     # forex candles incl. tick-volume (rate-limit retry)
    macro_service.py       # Finnhub economic calendar + news, per-pair event-risk
    signal_scheduler.py    # hourly: validated signal → Telegram alert + paper trade
    signal_service.py / telegram_service.py / trade_logger.py
  crew/                    # CrewAI desk-analyst agent, tasks, tools
  agents/market_agent.py   # full multi-TF SMC analysis used by the crew
  routes/                  # FastAPI endpoints (/dashboard, /signals, /crew-analysis, ...)
frontend/                  # React + Vite dashboard (Dockerfile + nginx reverse-proxy)
Dockerfile / docker-compose.yml      # app + monitor + dashboard
backtest.py                          # CLI backtest runner
```

---

## Known limitations (deliberately listed)

- **It's paper-only.** No live broker execution is wired into the running loop.
- **The edge is narrow and unproven live** — GBPUSD/EURUSD daily, small backtest sample.
  Forward-test on demo before trusting it.
- **`confluence_score` is not a win-probability** — it's a confluence checklist; testing
  showed it doesn't reliably rank winners.
- **Lower timeframes lose after costs** — by design the engine only runs Daily.
- Some detectors (swings/CHoCH) are simplified; killzone gating is approximate.

---

## Disclaimer

For research and education. Not financial advice. No warranty. Past/backtested performance
does not predict future results. You are responsible for your own trading decisions and for
complying with the laws and broker regulations of your jurisdiction.
# forex-ai-system
