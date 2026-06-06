from fastapi import APIRouter

from app.services.market_data import (
    get_forex_intraday
)

from app.smart_money.structure import (
    detect_swings
)

from app.smart_money.liquidity import (
    detect_equal_highs,
    detect_equal_lows
)

router = APIRouter()


@router.get("/liquidity")
def liquidity_zones(pair: str = "EURUSD"):

    candles = get_forex_intraday(pair)

    swings = detect_swings(candles)

    equal_highs = detect_equal_highs(
        swings["swing_highs"]
    )

    equal_lows = detect_equal_lows(
        swings["swing_lows"]
    )

    return {
        "buy_side_liquidity": equal_highs,
        "sell_side_liquidity": equal_lows
    }