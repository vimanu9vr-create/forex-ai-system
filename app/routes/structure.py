from fastapi import APIRouter

from app.services.market_data import (
    get_forex_intraday
)

from app.smart_money.structure import (
    detect_swings
)

router = APIRouter()


@router.get("/structure")
def market_structure(pair: str = "EURUSD"):

    candles = get_forex_intraday(pair)

    swings = detect_swings(candles)

    return swings