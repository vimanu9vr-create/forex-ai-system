from fastapi import APIRouter, Body

from app.config import DASHBOARD_PAIRS, DASHBOARD_TIMEFRAMES
from app.services.signal_service import get_live_signals
from app.services.intraday_signal_service import get_intraday_signals, intraday_cache_status
from app.crew.intraday_validator import validate_intraday_signal
from app.crew.intraday_redetector import redetect_intraday
from app.services.intraday_forward_test import forward_test_stats

router = APIRouter()


@router.get("/signals")
def get_signals():
    """Daily scanner feed — a read for EVERY dashboard pair x timeframe. High-probability setups
    sort to the top with full entry/SL/TP; low-conviction pairs appear as 'watch' rows. Multiple
    TFs (15m/1h/4h/1day) = 28 rows (7 pairs × 4 TFs)."""
    return get_live_signals(pairs=DASHBOARD_PAIRS, timeframes=DASHBOARD_TIMEFRAMES, show_all=True)


@router.get("/signals/intraday")
def get_intraday(tf: str = "15min", session: str = "london"):
    """Top-down liquidity-sweep engine (separate from the daily-edge /signals).
    tf = entry timeframe: '5min' or '15min'. session = 'london' (validated default) |
    'newyork' | 'both' — analyze each killzone separately. Gated to the Daily/4H bias."""
    return get_intraday_signals(tf=tf, session=session)


@router.get("/signals/intraday/status")
def get_intraday_status():
    return intraday_cache_status()


@router.post("/signals/intraday/validate")
def validate_intraday(signal: dict = Body(...)):
    """On-demand CrewAI desk verdict (TAKE/SKIP) on a specific 15m signal (judges the
    engine's exact levels — same signal)."""
    return validate_intraday_signal(signal)


@router.get("/signals/intraday/redetect")
def redetect_intraday_route(pair: str, tf: str = "15min", session: str = "london"):
    """INDEPENDENT second opinion: a CrewAI desk trader pulls its own candles, forms its own
    read of the sweep (direction + levels), and compares to the engine's signal (agree/disagree)."""
    sigs = get_intraday_signals(tf=tf, session=session)
    engine_sig = next((s for s in sigs if str(s.get("pair", "")).upper() == pair.upper()), None)
    return redetect_intraday(pair.upper(), tf=tf, session=session, engine_sig=engine_sig)


@router.get("/signals/intraday/forward-test")
def intraday_forward_test():
    """Demo-forward stats: outcomes of every intraday signal logged live over time
    (the real out-of-sample sample the small backtest lacks). Gross of costs."""
    return forward_test_stats()
