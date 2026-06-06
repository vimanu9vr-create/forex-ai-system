from fastapi import APIRouter

from app.services.market_data import (
    get_forex_intraday  
)

from app.smart_money.fvg import (
    detect_fvg
)
router = APIRouter()
@router.get("/fvg")
def analyze_fvg(pair: str = "EURUSD"):

    candles = get_forex_intraday(pair)

    fvg_zones = detect_fvg(candles)
    bullish_fvg_zones = fvg_zones["bullish_fvg_zones"]
    bearish_fvg_zones = fvg_zones["bearish_fvg_zones"]

    return {
        "bullish_fvg_zones": bullish_fvg_zones,
        "bearish_fvg_zones": bearish_fvg_zones
    }   