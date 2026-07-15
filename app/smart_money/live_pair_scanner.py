"""
live_pair_scanner — scans the configured strategy pairs/timeframe for the
dashboard /signals feed and the SignalScheduler.

Defaults to the validated edge: GBPUSD + EURUSD on the DAILY timeframe
(config.STRATEGY_PAIRS / STRATEGY_TIMEFRAME). Direction comes from a stacked-MA
trend filter (pullback-robust); the probability engine's multi_timeframe flag
reflects real trend confirmation; the score is surfaced as `confluence_score`.
"""

from app.config import STRATEGY_PAIRS, STRATEGY_TIMEFRAME
from app.services.market_data import get_forex_intraday
from app.smart_money.structure import detect_swings
from app.smart_money.liquidity import detect_equal_highs, detect_equal_lows
from app.smart_money.sweeps import detect_buy_side_sweeps, detect_sell_side_sweeps
from app.smart_money.choch import detect_bullish_choch, detect_bearish_choch
from app.smart_money.fvg import detect_fvg
from app.smart_money.bias import determine_market_bias
from app.smart_money.bos import detect_bullish_bos, detect_bearish_bos
from app.smart_money.order_blocks import detect_order_blocks
from app.smart_money.probability_engine import calculate_probability
from app.smart_money.killzones import detect_killzone


def _ma(values, period):
    return sum(values[-period:]) / period if len(values) >= period else None


def _trend_direction(candles) -> str:
    """Stacked-MA trend filter: 'buy' / 'sell' / 'neutral' (pullback-robust)."""
    closes = [c["close"] for c in candles]
    if len(closes) < 110:
        return "neutral"
    ma20, ma50, ma100 = _ma(closes, 20), _ma(closes, 50), _ma(closes, 100)
    ma50_prev = _ma(closes[:-10], 50)
    price = closes[-1]
    if ma20 > ma50 > ma100 and price > ma50 and ma50 > ma50_prev:
        return "buy"
    if ma20 < ma50 < ma100 and price < ma50 and ma50 < ma50_prev:
        return "sell"
    return "neutral"


def live_pair_scanner(pairs=None):
    scanned_pairs = []

    for pair in (pairs or STRATEGY_PAIRS):
        candles = get_forex_intraday(pair, interval=STRATEGY_TIMEFRAME, outputsize=300)
        if not candles or len(candles) < 110:
            continue

        swings = detect_swings(candles)
        equal_highs = detect_equal_highs(swings["swing_highs"])
        equal_lows = detect_equal_lows(swings["swing_lows"])

        buy_side_sweeps = detect_buy_side_sweeps(candles, liquidity_zones=equal_highs + equal_lows)
        sell_side_sweeps = detect_sell_side_sweeps(candles, liquidity_zones=equal_highs + equal_lows)
        sweeps_all = buy_side_sweeps + sell_side_sweeps

        choch_bullish = detect_bullish_choch(candles, swings["swing_highs"])
        choch_bearish = detect_bearish_choch(candles, swings["swing_lows"])
        bullish_bos = detect_bullish_bos(candles, swings["swing_highs"])
        bearish_bos = detect_bearish_bos(candles, swings["swing_lows"])

        fvg_zones = detect_fvg(candles)
        order_blocks = detect_order_blocks(candles)
        killzone_info = detect_killzone()

        direction = _trend_direction(candles)
        trend_confirmed = direction in ("buy", "sell")
        structure_bias = determine_market_bias(bullish_bos, bearish_bos, choch_bullish, choch_bearish)

        sweeps_arg = {"swept": len(sweeps_all) > 0, "sweeps": sweeps_all}
        choch_arg = {"choch": len(choch_bullish) + len(choch_bearish) > 0,
                     "bullish": choch_bullish, "bearish": choch_bearish}
        fvg_arg = {"present": bool(fvg_zones.get("bullish_fvg_zones") or fvg_zones.get("bearish_fvg_zones")),
                   "zones": fvg_zones}
        order_blocks_arg = {"present": bool(order_blocks.get("bullish_order_blocks") or order_blocks.get("bearish_order_blocks")),
                            "blocks": order_blocks}

        confluence = calculate_probability(
            sweeps=sweeps_arg,
            choch=choch_arg,
            killzone={"active": killzone_info.get("killzone") != "None", "info": killzone_info},
            multi_timeframe={"valid": trend_confirmed},
            fvg=fvg_arg,
            order_blocks=order_blocks_arg,
        )
        confluence_score = confluence.get("probability_score", 0)

        signal_data = {
            "confluence_score": confluence_score,
            "killzone_active": killzone_info,
            "bias": structure_bias,
            "trend_direction": direction,
            "trend_confirmed": trend_confirmed,
        }

        scanned_pairs.append({
            "pair": pair,
            "probability_score": confluence_score,
            "confluence_score": confluence_score,
            "direction": direction,
            "htf_aligned": trend_confirmed,
            "session": killzone_info.get("killzone", "N/A"),
            "candles": candles,
            "sniper_signal": {"entry": trend_confirmed and confluence_score >= 80, "direction": direction},
            "sweeps": sweeps_all,
            "choch": [choch_bullish, choch_bearish],
            "fvg_zones": fvg_zones,
            "order_blocks": order_blocks,
            "signal_data": signal_data,
        })

    if not scanned_pairs:
        return {"message": "No pairs scanned successfully."}

    best_pair = max(scanned_pairs, key=lambda x: x["confluence_score"])
    return {"best_pair": best_pair, "all_scanned_pairs": scanned_pairs}
