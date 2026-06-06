from fastapi import APIRouter

from app.services.market_data import (
    get_forex_intraday
)

from app.smart_money.structure import (
    detect_swings
)   

from app.smart_money.premium_discount import (
    calculate_premium_discount
)
router = APIRouter()

@router.get("/premium-discount")

def premium_discount(pair: str = "EURUSD"):

    candles = get_forex_intraday(pair)

    swings = detect_swings(candles)

    swing_highs = swings["swing_highs"]
    swing_lows = swings["swing_lows"]

    if not swing_highs or not swing_lows:
        return {"error": "Not enough swing data to calculate premium/discount."}


    latest_high = (swings["swing_highs"][-1]["price"] )
    latest_low = (swings["swing_lows"][-1]["price"]  )

    current_price = (candles[-1]["close"] )


    result = calculate_premium_discount(
        latest_high,
        latest_low,
        current_price
    )   
    return result
