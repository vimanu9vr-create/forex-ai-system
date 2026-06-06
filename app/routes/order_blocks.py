from fastapi import APIRouter

from app.services.market_data import (
    get_forex_intraday
)

from app.smart_money.order_blocks import (
    detect_order_blocks
)   
router = APIRouter()
@router.get("/order-blocks")
def analyze_order_blocks(pair: str = "EURUSD"):

    candles = get_forex_intraday(pair)

    order_blocks = detect_order_blocks(candles)

    return {
        "order_blocks": order_blocks
    }