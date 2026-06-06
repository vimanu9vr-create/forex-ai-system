"""
generate_trade_setup — Institutional SMC entry model.

Entry logic:
  LONG:  sell-side sweep + bullish CHOCH/BOS confirmed
         Entry  = last bullish order block top (or FVG bottom if present)
         SL     = below the sweep low − ATR buffer (minimum 20 pips / 10 pips JPY)
         TP     = next buy-side liquidity (swing high / equal highs)
         Min RR = 1.5 enforced; setup discarded if not achievable

  SHORT: buy-side sweep + bearish CHOCH/BOS confirmed
         Entry  = last bearish order block bottom (or FVG top if present)
         SL     = above the sweep high + ATR buffer
         TP     = next sell-side liquidity (swing low / equal lows)
"""

from app.smart_money.order_blocks import detect_order_blocks
from app.smart_money.fvg import detect_fvg
from app.config import MIN_RISK_REWARD


def _pip_size(pair: str) -> float:
    return 0.01 if "JPY" in pair.upper() else 0.0001


def _atr(candles: list, period: int = 14) -> float:
    if len(candles) < period + 1:
        return 0.001
    trs = []
    for i in range(1, period + 1):
        c = candles[-i]
        p = candles[-i - 1]
        tr = max(
            c["high"] - c["low"],
            abs(c["high"] - p["close"]),
            abs(c["low"]  - p["close"]),
        )
        trs.append(tr)
    return sum(trs) / len(trs)


def _round_price(price: float, pair: str) -> float:
    return round(price, 3 if "JPY" in pair.upper() else 5)


def generate_trade_setup(
    bias,
    sell_side_sweeps,
    bullish_bos,
    bullish_choch,
    buy_side_sweeps,
    bearish_bos,
    bearish_choch,
    candles: list = None,
    pair: str = "EURUSD",
    fvg_zones: dict = None,
    order_blocks: dict = None,
) -> list:
    """
    Returns list of setup dicts with entry_price, stop_loss, take_profit, rr_ratio.
    Minimum RR 1.5 enforced — setups that can't achieve it are discarded.
    """
    if not candles or len(candles) < 10:
        return []

    setups = []
    pip = _pip_size(pair)
    atr_val = _atr(candles)
    # SL buffer = 1.2× ATR but at minimum 20 pips (prevents 10-pip SL nonsense)
    sl_buffer = max(atr_val * 1.2, pip * 20)
    last_close = candles[-1]["close"]

    if order_blocks is None:
        order_blocks = detect_order_blocks(candles)
    if fvg_zones is None:
        fvg_zones = detect_fvg(candles)

    # ── LONG ─────────────────────────────────────────────────────────────
    if (
        isinstance(bias, dict) and bias.get("bias") == "bullish"
        and len(sell_side_sweeps) > 0
        and (len(bullish_bos) > 0 or len(bullish_choch) > 0)
    ):
        entry, sl, tp = _long_prices(
            candles, sell_side_sweeps, order_blocks, fvg_zones,
            sl_buffer, last_close
        )
        # Anchor to live price: only keep the setup if price is still inside the
        # stop↔target zone (not already stopped out or past the target).
        if entry and sl and tp and sl < last_close < tp:
            risk   = entry - sl
            reward = tp - entry
            rr     = reward / risk if risk > 0 else 0
            if rr >= MIN_RISK_REWARD:
                setups.append({
                    "signal":      "BUY",
                    "type":        "buy",
                    "entry_price": _round_price(entry, pair),
                    "stop_loss":   _round_price(sl,    pair),
                    "take_profit": _round_price(tp,    pair),
                    "current_price": _round_price(last_close, pair),
                    "entry_type":  "limit" if abs(last_close - entry) > pip * 2 else "market",
                    "distance_to_entry_pips": round(abs(last_close - entry) / pip, 1),
                    "rr_ratio":    round(rr, 2),
                    "confidence":  85,
                    "reason": (
                        "Sell-side sweep + bullish CHOCH/BOS + bullish HTF bias. "
                        "Entry at OB/FVG zone, SL below sweep low, TP at next buy-side liquidity."
                    ),
                })

    # ── SHORT ────────────────────────────────────────────────────────────
    if (
        isinstance(bias, dict) and bias.get("bias") == "bearish"
        and len(buy_side_sweeps) > 0
        and (len(bearish_bos) > 0 or len(bearish_choch) > 0)
    ):
        entry, sl, tp = _short_prices(
            candles, buy_side_sweeps, order_blocks, fvg_zones,
            sl_buffer, last_close
        )
        # Anchor to live price: only keep the setup if price is still inside the
        # target↔stop zone (not already stopped out or past the target).
        if entry and sl and tp and tp < last_close < sl:
            risk   = sl - entry
            reward = entry - tp
            rr     = reward / risk if risk > 0 else 0
            if rr >= MIN_RISK_REWARD:
                setups.append({
                    "signal":      "SELL",
                    "type":        "sell",
                    "entry_price": _round_price(entry, pair),
                    "stop_loss":   _round_price(sl,    pair),
                    "take_profit": _round_price(tp,    pair),
                    "current_price": _round_price(last_close, pair),
                    "entry_type":  "limit" if abs(last_close - entry) > pip * 2 else "market",
                    "distance_to_entry_pips": round(abs(last_close - entry) / pip, 1),
                    "rr_ratio":    round(rr, 2),
                    "confidence":  85,
                    "reason": (
                        "Buy-side sweep + bearish CHOCH/BOS + bearish HTF bias. "
                        "Entry at OB/FVG zone, SL above sweep high, TP at next sell-side liquidity."
                    ),
                })

    return setups


# ── Price helpers ─────────────────────────────────────────────────────────

def _long_prices(candles, sweeps, order_blocks, fvg_zones, sl_buffer, last_close):
    # SL — below the lowest sweep candle low with buffer
    sweep_lows = []
    for s in sweeps:
        if not s:
            continue
        p = s.get("price") or s.get("sweep_price") or s.get("low")
        if p:
            sweep_lows.append(float(p))
    sweep_low = min(sweep_lows) if sweep_lows else min(c["low"] for c in candles[-20:])
    sl = sweep_low - sl_buffer

    # Entry — OB top or FVG bottom; must be ABOVE the sweep low (price reversed up)
    raw_entry = _best_long_entry(order_blocks, fvg_zones, last_close)
    # Ensure entry is above sweep_low so risk = entry - sl >= sl_buffer
    entry = max(raw_entry, sweep_low + sl_buffer * 0.1)
    # Hard floor: entry must be above SL
    if entry <= sl:
        entry = sl + sl_buffer

    # TP — highest swing high above entry at ≥ 1.5× risk distance
    min_tp = entry + (entry - sl) * 1.5
    candidates = [c["high"] for c in candles[-80:] if c["high"] >= min_tp]
    tp = max(candidates) if candidates else entry + (entry - sl) * 2.0

    return entry, sl, tp


def _short_prices(candles, sweeps, order_blocks, fvg_zones, sl_buffer, last_close):
    # SL — above the highest sweep candle high with buffer
    sweep_highs = []
    for s in sweeps:
        if not s:
            continue
        p = s.get("price") or s.get("sweep_price") or s.get("high")
        if p:
            sweep_highs.append(float(p))
    sweep_high = max(sweep_highs) if sweep_highs else max(c["high"] for c in candles[-20:])
    sl = sweep_high + sl_buffer

    # Entry — OB bottom or FVG top; must be BELOW the sweep high (price reversed down)
    raw_entry = _best_short_entry(order_blocks, fvg_zones, last_close)
    entry = min(raw_entry, sweep_high - sl_buffer * 0.1)
    if entry >= sl:
        entry = sl - sl_buffer

    # TP — lowest swing low below entry at ≥ 1.5× risk distance
    min_tp = entry - (sl - entry) * 1.5
    candidates = [c["low"] for c in candles[-80:] if c["low"] <= min_tp]
    tp = min(candidates) if candidates else entry - (sl - entry) * 2.0

    return entry, sl, tp


def _best_long_entry(order_blocks, fvg_zones, fallback):
    obs = (order_blocks or {}).get("bullish_order_blocks", [])
    if obs:
        latest = max(obs, key=lambda x: x.get("index", 0))
        return max(latest.get("start", 0), latest.get("end", 0))
    fvgs = (fvg_zones or {}).get("bullish_fvg_zones", [])
    if fvgs:
        latest = max(fvgs, key=lambda x: x.get("index", 0))
        return latest.get("start", fallback)
    return fallback


def _best_short_entry(order_blocks, fvg_zones, fallback):
    obs = (order_blocks or {}).get("bearish_order_blocks", [])
    if obs:
        latest = max(obs, key=lambda x: x.get("index", 0))
        return min(latest.get("start", float("inf")), latest.get("end", float("inf")))
    fvgs = (fvg_zones or {}).get("bearish_fvg_zones", [])
    if fvgs:
        latest = max(fvgs, key=lambda x: x.get("index", 0))
        return latest.get("end", fallback)
    return fallback
