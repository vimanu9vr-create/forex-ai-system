import os
from pathlib import Path
from dotenv import load_dotenv

# Telegram + OpenAI + TwelveData keys live in app/.env. A bare load_dotenv()
# resolved to the project-root .env (which lacks the Telegram keys), so the bot
# token came back None and every alert POSTed to /botNone/sendMessage → 404.
# Load app/.env explicitly first, then fall back to the project-root .env.
load_dotenv(Path(__file__).resolve().parent / ".env")  # app/.env (canonical)
load_dotenv()                                           # project-root .env (fallback)

# Accept either OPENAI_API_KEY (canonical) or the legacy OPEN_AI_API name used in
# .env, then export the canonical name so CrewAI / litellm can authenticate.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI_API")
if OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./forex_ai.db")
TWELVEDATA_API_KEY=os.getenv("TWELVEDATA_API_KEY")
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
# Polygon per-minute call cap. FREE tier = 5/min; bursting a 7-pair x 3-TF scan past it gets
# 429'd and DROPS pairs (e.g. the one trending pair gets no data -> no signal). We pace under
# this so fetches never fail. Raise it if you're on a paid Polygon plan. 0 = no throttle.
POLYGON_MAX_CALLS_PER_MIN = int(os.getenv("POLYGON_MAX_CALLS_PER_MIN", "5"))

# ── AWS (boto3) — durable artifact storage on S3 ─────────────────────────────
# Set AWS_S3_BUCKET + credentials (env vars locally, or an IAM task role on ECS/EC2) to
# persist the intraday forward-test log + backtest artifacts to S3, so the paper-trading
# track record survives container/instance replacement. All S3 calls no-op gracefully if unset.
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "")
AWS_REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
OANDA_API_KEY = os.getenv("OANDA_API_KEY")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")
OANDA_ENVIRONMENT = os.getenv("OANDA_ENVIRONMENT", "practice")
OANDA_LIVE_TRADING = os.getenv("OANDA_LIVE_TRADING", "false")
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "admin")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")

# ── Risk parameters ─────────────────────────────────────────────────────────
# Minimum reward:risk a setup must offer to be emitted. Institutional spec = 3.0
# (1:3). Higher = fewer, higher-quality setups. Override via MIN_RISK_REWARD env.
MIN_RISK_REWARD = float(os.getenv("MIN_RISK_REWARD", "3.0"))

# ── Live strategy: the cost + out-of-sample validated edge ───────────────────
# Only GBPUSD + EURUSD on the DAILY timeframe survived costs AND out-of-sample
# testing, so that's what the live engine trades. Override via env vars.
STRATEGY_PAIRS = [p.strip().upper() for p in os.getenv("STRATEGY_PAIRS", "GBPUSD,EURUSD").split(",") if p.strip()]
STRATEGY_TIMEFRAME = os.getenv("STRATEGY_TIMEFRAME", "1day")
SCAN_INTERVAL_SECONDS = int(os.getenv("SCAN_INTERVAL_SECONDS", "3600"))  # hourly; daily signals change slowly

# ── Intraday engine: SEPARATE, UNVALIDATED 15m liquidity-sweep day-trading engine ──
# This is NOT the cost/OOS-validated daily edge above. It is a distinct sweep ->
# displacement -> market-structure-shift -> FVG/OTE reversal engine, killzone-gated,
# built to be backtested before it is trusted. Majors with the tightest intraday
# spreads + cleanest liquidity raids. Override via env.
# Full majors for analysis across both sessions. NOTE: only EURUSD/GBPUSD/USDJPY were
# in the London backtest (+0.68R); AUD/CAD/CHF/NZD are observation-only until backtested.
# More pairs = slower scan (each = Daily+4H+entryTF fetch). Trim via env if it lags.
INTRADAY_PAIRS = [p.strip().upper() for p in os.getenv("INTRADAY_PAIRS", "EURUSD,GBPUSD,USDJPY,AUDUSD,USDCAD,USDCHF,NZDUSD").split(",") if p.strip()]
INTRADAY_TIMEFRAME = os.getenv("INTRADAY_TIMEFRAME", "15min")
INTRADAY_MIN_RR = float(os.getenv("INTRADAY_MIN_RR", "1.5"))  # nearer target converts more often (was 2.0; backtest: lifts net edge)

# ── Intraday tuning knobs (the desk corrections; backtested in backtest_intraday_tune.py) ──
# The original wick-tight stop + 2R target LOST net of cost (-0.06R: death by stop-out —
# the raid double-taps and runs the stop before the reversal). The tuning harness tested
# principled corrections net of 1.5-pip spread + out-of-sample; WINNERS are the defaults
# below. Best config "london_only" (sl x1.0, RR 1.5, London-only): +0.68R net, 68% win,
# positive in BOTH OOS halves on a SMALL sample (19 trades). All env-overridable.
INTRADAY_SL_ATR_MULT = float(os.getenv("INTRADAY_SL_ATR_MULT", "1.0"))      # stop buffer beyond the sweep wick, in ATR (wider survives the double-tap; lifted win% 33->50)
INTRADAY_MIN_SWEEP_ATR = float(os.getenv("INTRADAY_MIN_SWEEP_ATR", "0.0"))  # sweep must penetrate the pool by >= this*ATR (a real raid; ON dropped sample to 7 trades, left OFF)
INTRADAY_MIN_DISP_BODY_ATR = float(os.getenv("INTRADAY_MIN_DISP_BODY_ATR", "0.0"))  # the MSS-breaking candle body must be >= this*ATR (true displacement)
INTRADAY_EQUAL_POOLS_ONLY = os.getenv("INTRADAY_EQUAL_POOLS_ONLY", "false").lower() in ("1", "true", "yes")  # only raid engineered equal-highs/lows (similar edge, fewer trades — OFF)

# Restrict entries to specific killzones (exact names: "London Open", "New York Open").
# Comma-separated; empty/unset => both London & NY. BACKTEST: New York bleeds consistently
# across pairs/configs (EURUSD New -4.79R, GBPUSD New -3.07R) while London pays — so the
# validated default is LONDON ONLY. Set INTRADAY_KILLZONES="London Open,New York Open" to watch NY.
_kz = [k.strip() for k in os.getenv("INTRADAY_KILLZONES", "London Open").split(",") if k.strip()]
INTRADAY_KILLZONES = set(_kz) if _kz else None

# HTF handling: the +0.68R backtest ran WITHOUT a directional HTF filter (htf_bias=None),
# but the live service was standing aside every HTF-neutral pair — far stricter than what was
# validated, so the dashboard was empty most of the time (e.g. 6/7 majors neutral). Default now:
# trade WITH a clear Daily+4H bias (top-down), but on a NEUTRAL pair scan BOTH directions (the
# validated behavior) instead of standing aside. Set True to restore strict top-down-only.
INTRADAY_STAND_ASIDE_NEUTRAL = os.getenv("INTRADAY_STAND_ASIDE_NEUTRAL", "false").lower() in ("1", "true", "yes")

# Which sessions the intraday alert scheduler pushes to Telegram (and forward-test logs).
# London is the validated edge; New York UNDERPERFORMED in the backtest (net loss) but is
# enabled here so its live signals are delivered + tracked. "london" / "newyork" / both.
INTRADAY_ALERT_SESSIONS = {s.strip().lower() for s in
                           os.getenv("INTRADAY_ALERT_SESSIONS", "london,newyork").split(",") if s.strip()}
