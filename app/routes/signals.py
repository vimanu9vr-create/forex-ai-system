from fastapi import APIRouter, Body

from app.services.signal_service import get_live_signals
from app.services.intraday_signal_service import get_intraday_signals, intraday_cache_status
from app.crew.intraday_validator import validate_intraday_signal

router = APIRouter()


@router.get("/signals")
def get_signals():
    return get_live_signals()


@router.get("/signals/intraday")
def get_intraday(tf: str = "15min"):
    """Top-down liquidity-sweep engine (separate from the daily-edge /signals).
    tf = entry timeframe: '5min' or '15min'. Gated to the Daily/4H bias direction."""
    return get_intraday_signals(tf=tf)


@router.get("/signals/intraday/status")
def get_intraday_status():
    return intraday_cache_status()


@router.post("/signals/intraday/validate")
def validate_intraday(signal: dict = Body(...)):
    """On-demand CrewAI desk verdict (TAKE/SKIP) on a specific 15m signal."""
    return validate_intraday_signal(signal)
