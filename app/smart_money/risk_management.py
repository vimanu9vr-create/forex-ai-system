"""
trade_levels — structure-based entry / stop / target.

Replaces the old "enter at market, SL at the 10-bar extreme, TP at a mechanical
2× risk" logic, which chased price after the move had already happened and was
therefore stopped out systematically.

Discipline rules now enforced:
  - Only LONG when price sits in the DISCOUNT half of the recent range
    (buy the pullback, never the top); only SHORT in the PREMIUM half.
  - Stop sits beyond the structural swing (with an ATR/pip buffer), not at an
    arbitrary fixed distance.
  - Target is the opposing structural liquidity (range high for longs, range
    low for shorts) — a level price actually reaches — not a fabricated 2×.
  - Setup is REJECTED (valid=False) unless it offers >= 1.5R. The scanner /
    signal service drop rejected setups instead of showing a losing signal.
"""

from app.config import MIN_RISK_REWARD

LOOKBACK = 20               # candles of structure used for swing high/low + range
MIN_RR   = MIN_RISK_REWARD  # reject setups below this R:R (institutional spec = 1:3)


def _pip_size(pair: str) -> float:
    return 0.01 if "JPY" in pair.upper() else 0.0001


def _digits(pair: str) -> int:
    return 3 if "JPY" in pair.upper() else 5


def trade_levels(pair, direction, candles):
    """
    Returns a dict with entry_price / stop_loss / take_profit / risk_reward and
    a `valid` flag. When `valid` is False the caller should skip the signal.
    `direction` is case-insensitive and accepts BUY/LONG and SELL/SHORT.
    """
    pip = _pip_size(pair)
    digits = _digits(pair)

    def reject(reason):
        return {
            "pair": pair, "valid": False, "reason": reason,
            "entry_price": 0, "stop_loss": 0, "take_profit": 0, "risk_reward": "N/A",
        }

    side = str(direction or "").strip().upper()
    if side in ("LONG",):
        side = "BUY"
    elif side in ("SHORT",):
        side = "SELL"
    if side not in ("BUY", "SELL"):
        return reject("No directional bias")
    if not candles or len(candles) < LOOKBACK:
        return reject("Insufficient candle history")

    window = candles[-LOOKBACK:]
    current_price = candles[-1]["close"]
    swing_high = max(c["high"] for c in window)
    swing_low = min(c["low"] for c in window)
    price_range = swing_high - swing_low
    if price_range <= 0:
        return reject("Flat / no range")

    # Position of price within the range: 0.0 = at the low, 1.0 = at the high.
    position = (current_price - swing_low) / price_range

    # Stop buffer: half the average candle range, floored at 8 pips, so the
    # stop sits just beyond structure rather than on it.
    avg_candle = sum(c["high"] - c["low"] for c in window) / len(window)
    buffer = max(avg_candle * 0.5, pip * 8)

    if side == "BUY":
        entry = current_price
        stop = swing_low - buffer
        target = swing_high                       # opposing liquidity
        risk = entry - stop
        reward = target - entry
        located = position <= 0.5                 # in the discount half (buy the pullback)
        mislocated = f"price in premium ({position:.0%} of range)"
    else:  # SELL
        entry = current_price
        stop = swing_high + buffer
        target = swing_low
        risk = stop - entry
        reward = entry - target
        located = position >= 0.5                 # in the premium half
        mislocated = f"price in discount ({position:.0%} of range)"

    if risk <= 0 or reward <= 0:
        return reject("Non-positive risk or reward")

    rr = reward / risk
    dir_sign = 1 if side == "BUY" else -1

    # A+ setup = located in the right half AND >= MIN_RR. Otherwise return the SAME computed
    # levels flagged valid=False + a reason, so the dashboard can show an INDICATIVE trade. The
    # scheduler/alerts path (show_all=False) still drops non-valid setups.
    if located and rr >= MIN_RR:
        valid = True
        reason = ("Discount pullback long → range high" if side == "BUY"
                  else "Premium pullback short → range low")
    elif not located:
        valid, reason = False, f"Indicative only — {mislocated}, not a pullback entry"
    else:
        valid, reason = False, f"Indicative only — R:R 1:{rr:.1f} below {MIN_RR}"

    return {
        "pair": pair,
        "valid": valid,
        "entry_price": round(entry, digits),
        "stop_loss": round(stop, digits),
        "take_profit": round(target, digits),
        "risk_reward": f"1:{rr:.1f}",
        "invalidation": round(stop, digits),
        "invalidation_note": (
            f"H1 close beyond {round(stop, digits)} invalidates the "
            f"{'long' if side == 'BUY' else 'short'}."
        ),
        "management": {
            "tp1": round(entry + dir_sign * risk, digits),
            "tp2": round(entry + dir_sign * 2 * risk, digits),
            "tp3": round(target, digits),
            "plan": (
                "TP1 (1R): close 1/3, move SL to breakeven. "
                "TP2 (2R): close 1/3, trail behind the last H1 swing. "
                "TP3 (structural target): close the runner."
            ),
        },
        "reason": reason,
    }
