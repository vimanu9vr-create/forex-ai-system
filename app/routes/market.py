from fastapi import APIRouter
from app.services.market_data import (get_forex_intraday)

router = APIRouter()

@router.get("/market")
def market_data(pair: str = "EURUSD"):
    data = get_forex_intraday(pair)
    return {"candles": data}

