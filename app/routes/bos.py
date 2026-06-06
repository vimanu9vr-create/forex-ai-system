from fastapi import APIRouter
from app.services.market_data import get_forex_intraday
from app.smart_money.structure import detect_swings
from app.smart_money.liquidity import detect_equal_highs, detect_equal_lows
from app.smart_money.sweeps import detect_buy_side_sweeps, detect_sell_side_sweeps
from app.smart_money.bos import detect_bullish_bos, detect_bearish_bos

router = APIRouter()


@router.get("/bos")
def bos(pair: str = "EURUSD"):
    candles = get_forex_intraday(pair)
    if not candles:
        return {"bos": [], "error": f"No candle data for {pair}"}

    swings = detect_swings(candles)
    equal_highs = detect_equal_highs(swings["swing_highs"])
    equal_lows = detect_equal_lows(swings["swing_lows"])
    liquidity_zones = equal_highs + equal_lows

    sweeps = detect_buy_side_sweeps(candles, liquidity_zones)
    sweeps += detect_sell_side_sweeps(candles, liquidity_zones)

    bos_signals = detect_bullish_bos(candles, swings["swing_highs"])
    bos_signals += detect_bearish_bos(candles, swings["swing_lows"])

    return {"bos": bos_signals}
