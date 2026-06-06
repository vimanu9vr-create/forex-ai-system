from fastapi import APIRouter

from app.services.market_data import get_forex_intraday
from app.smart_money.structure import detect_swings
from app.smart_money.liquidity import detect_equal_highs, detect_equal_lows
from app.smart_money.sweeps import detect_buy_side_sweeps, detect_sell_side_sweeps
from app.smart_money.bos import detect_bullish_bos, detect_bearish_bos
from app.smart_money.choch import detect_bullish_choch, detect_bearish_choch
from app.smart_money.bias import determine_market_bias
from app.smart_money.setups import generate_trade_setup

router = APIRouter()


@router.get("/setups")
def setups(pair: str = "EURUSD"):

    candles = get_forex_intraday(pair)

    swings = detect_swings(candles)
    swing_highs = swings["swing_highs"]
    swing_lows = swings["swing_lows"]

    equal_highs = detect_equal_highs(swing_highs)
    equal_lows = detect_equal_lows(swing_lows)
    liquidity_zones = equal_highs + equal_lows

    buy_side_sweeps = detect_buy_side_sweeps(candles, liquidity_zones)
    sell_side_sweeps = detect_sell_side_sweeps(candles, liquidity_zones)
    sweeps = buy_side_sweeps + sell_side_sweeps

    bullish_bos = detect_bullish_bos(candles, swing_highs)
    bearish_bos = detect_bearish_bos(candles, swing_lows)

    bullish_choch = detect_bullish_choch(candles, swing_highs)
    bearish_choch = detect_bearish_choch(candles, swing_lows)

    bias = determine_market_bias(
        bullish_bos=bullish_bos,
        bearish_bos=bearish_bos,
        bullish_choch=bullish_choch,
        bearish_choch=bearish_choch,
    )

    trade_setups = generate_trade_setup(
        bias,
        sell_side_sweeps,
        bullish_bos,
        bullish_choch,
        buy_side_sweeps,
        bearish_bos,
        bearish_choch,
        candles=candles,
        pair=pair,
    )

    return {
        "pair": pair,
        "bias": bias,
        "setups": trade_setups,
        "bos": {"bullish": bullish_bos, "bearish": bearish_bos},
        "choch": {"bullish": bullish_choch, "bearish": bearish_choch},
        "sweeps": sweeps,
        "liquidity": {"buy_side": equal_highs, "sell_side": equal_lows},
    }
