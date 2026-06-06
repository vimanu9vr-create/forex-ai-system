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
INTRADAY_PAIRS = [p.strip().upper() for p in os.getenv("INTRADAY_PAIRS", "EURUSD,GBPUSD,USDJPY").split(",") if p.strip()]
INTRADAY_TIMEFRAME = os.getenv("INTRADAY_TIMEFRAME", "15min")
INTRADAY_MIN_RR = float(os.getenv("INTRADAY_MIN_RR", "2.0"))  # liquidity-to-liquidity day trades
