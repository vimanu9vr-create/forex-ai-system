"""
live_pair_scanner — scans the configured strategy pairs/timeframe for the
dashboard /signals feed and the SignalScheduler.

Defaults to the validated edge: GBPUSD + EURUSD on the DAILY timeframe
(config.STRATEGY_PAIRS / STRATEGY_TIMEFRAME). Direction comes from a stacked-MA
trend filter (pullback-robust); the probability engine's multi_timeframe flag
reflects real trend confirmation; the score is surfaced as `confluence_score`.
"""

from app.config import STRATEGY_PAIRS, STRATEGY_TIMEFRAME, DASHBOARD_TIMEFRAMES
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


def live_pair_scanner(pairs=None, timeframes=None):
    """Scan pairs x timeframes for the dashboard. Fetches Daily/4H once per pair for HTF bias,
    then scans each TF against that. Can return 28 rows (7 pairs × 4 TFs)."""
    scanned_pairs = []
    tfs = timeframes or (STRATEGY_TIMEFRAME,)

    for pair in (pairs or STRATEGY_PAIRS):
        # Daily fetched ONCE per pair for the stacked-MA trend filter (300 candles so the
        # 110-bar trend actually computes — the old 100 always returned neutral). Reused for
        # the 1day row below, so it's never double-fetched. (Dropped the dead 4H fetch.)
        daily = get_forex_intraday(pair, interval="1day", outputsize=300) or []
        direction = _trend_direction(daily) if len(daily) >= 110 else "neutral"
        trend_confirmed = direction in ("buy", "sell")

        for tf in tfs:
            # Reuse the daily candles for the 1day row instead of re-fetching them.
            candles = daily if tf == "1day" else get_forex_intraday(pair, interval=tf, outputsize=300)
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

            # direction/trend_confirmed computed once per pair (above) from the daily stacked-MA.
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
                "timeframe": tf,
                "probability_score": confluence_score,
                "confluence_score": confluence_score,
                "direction": direction,
                "htf_aligned": trend_confirmed,
                "session": killzone_info.get("killzone", "N/A"),
                # Only the last ~40 candles are needed downstream (trade_levels uses the last 20).
                # Retaining all 300 × 28 rows OOM-killed the container (exit 137). Keep it small.
                "candles": candles[-40:],
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
