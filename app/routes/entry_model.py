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

from app.smart_money.sweeps import (
    detect_buy_side_sweeps,
    detect_sell_side_sweeps
)

from app.smart_money.choch import (
    detect_bullish_choch,
    detect_bearish_choch
)   

from app.smart_money.bos import (
    detect_bullish_bos,
    detect_bearish_bos
)

from app.smart_money.fvg import (
    detect_fvg
)
from app.smart_money.bias import (
    determine_market_bias
)
from app.smart_money.entry_model import (
    entry_model
)
router = APIRouter()
@router.get("/entry-model")
def analyze_entry_model(pair: str = "EURUSD"):

    candles = get_forex_intraday(pair)

    swings = detect_swings(candles)


    equal_highs = detect_equal_highs(swings["swing_highs"])

    equal_lows = detect_equal_lows(
        swings["swing_lows"]
    )

    buy_side_sweeps = detect_buy_side_sweeps(
        candles,
        liquidity_zones=equal_highs + equal_lows
    )

    sell_side_sweeps = detect_sell_side_sweeps(
        candles,
        liquidity_zones=equal_highs + equal_lows
    )

    choch_bullish = detect_bullish_choch(
        candles,
        swing_highs=swings["swing_highs"]   
    )

    choch_bearish = detect_bearish_choch(
        candles,
        swing_lows=swings["swing_lows"]
    )

    fvg_zones = detect_fvg(candles)

    bos_bullish = detect_bullish_bos(candles, swings["swing_highs"])
    bos_bearish = detect_bearish_bos(candles, swings["swing_lows"])

    bias = determine_market_bias(
        bullish_bos=bos_bullish,
        bearish_bos=bos_bearish,
        bullish_choch=choch_bullish,
        bearish_choch=choch_bearish
    )

    entry_setups = entry_model(
        sweeps=buy_side_sweeps + sell_side_sweeps,
        choch=choch_bullish + choch_bearish,
        fvg={"bullish_fvg_zones": fvg_zones["bullish_fvg_zones"],
             "bearish_fvg_zones": fvg_zones["bearish_fvg_zones"]},
        bias=bias
    )

    return {
        "entry_setups": entry_setups,
        "bias": bias,
        "fvg_zones": fvg_zones,
        "choch": choch_bullish + choch_bearish,
        "sweeps": buy_side_sweeps + sell_side_sweeps,
        "swings": swings
    }