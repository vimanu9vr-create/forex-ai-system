"""
intraday_engine — dedicated 15m liquidity-sweep REVERSAL engine.

This is a SEPARATE decision logic from live_pair_scanner (the daily stacked-MA
trend engine). It encodes the ICT intraday model end to end:

  1. Liquidity pool   : equal highs/lows + swing extremes (where stops rest)
  2. Sweep            : price wicks through the pool and closes back inside (stop hunt)
  3. Killzone gate    : the sweep must occur in the London or New York killzone
  4. Displacement+MSS : a strong move the other way that breaks the last opposing
                        swing (market structure shift) — confirms the reversal
  5. Entry            : the FVG left by the displacement, else OTE (70.5% retrace)
  6. SL / TP          : SL beyond the sweep extreme; TP at the nearest opposite
                        liquidity pool that still satisfies min RR
  7. Risk             : INTRADAY_MIN_RR enforced; otherwise the setup is rejected

`analyze_intraday(pair, candles)` is pure — candles in, one signal dict or None
out — so the backtester replays it bar-by-bar with no lookahead.

Naming note: `quality_score` is an honest confluence CHECKLIST (0-100), NOT a
measured win-probability. This engine is UNVALIDATED until backtested.
"""

from datetime import datetime

from app.config import INTRADAY_MIN_RR
from app.smart_money.structure import detect_swings
from app.smart_money.liquidity import detect_equal_highs, detect_equal_lows
from app.smart_money.sweeps import detect_buy_side_sweeps, detect_sell_side_sweeps
from app.smart_money.fvg import detect_fvg
from app.smart_money.killzones import in_killzone

# ── Tunables (bars are 15m) ─────────────────────────────────────────────────
SWING_LOOKBACK   = 2     # fractal width — less noisy than the default 1 on 15m
RECENT_BARS      = 20    # sweep must have happened within the last ~5h
RECENT_AFTER     = 10    # MSS confirmation must be within the last ~2.5h (still fresh)
DISPLACEMENT_ATR = 1.2   # reversal leg must span >= 1.2x ATR to count as displacement
STRONG_BODY_ATR  = 0.6   # at least one candle body >= 0.6x ATR inside the displacement
MIN_CANDLES      = 60

# Quality filters — baseline OFF (0.0 / False); the backtester sweeps these and the
# winning values are baked in here. See analyze_intraday() docstring.
MIN_SWEEP_ATR     = 0.0   # sweep must penetrate the level by >= this * ATR (real raid)
MIN_DISP_BODY_ATR = 0.0   # the MSS-breaking candle body must be >= this * ATR
EQUAL_POOLS_ONLY  = False  # only sweep engineered equal-highs/lows (drop lone swings)


def _pip(pair: str) -> float:
    return 0.01 if "JPY" in pair.upper() else 0.0001


def _round(price: float, pair: str) -> float:
    return round(price, 3 if "JPY" in pair.upper() else 5)


def _atr(candles: list, period: int = 14) -> float:
    if len(candles) < period + 1:
        return 0.001
    trs = []
    for i in range(1, period + 1):
        c, p = candles[-i], candles[-i - 1]
        trs.append(max(c["high"] - c["low"],
                       abs(c["high"] - p["close"]),
                       abs(c["low"] - p["close"])))
    return sum(trs) / len(trs)


def _ma(values, period):
    return sum(values[-period:]) / period if len(values) >= period else None


def _stacked_ma_dir(candles):
    """Pullback-robust stacked-MA trend read: 'buy' / 'sell' / 'neutral'."""
    closes = [c["close"] for c in (candles or [])]
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


def htf_bias_from(daily, h4):
    """Top-down bias — Daily leads, 4H must confirm or be neutral.
    Returns ('bullish'|'bearish'|'neutral', daily_dir, h4_dir)."""
    d = _stacked_ma_dir(daily)
    h = _stacked_ma_dir(h4)
    if d == "buy" and h != "sell":
        return "bullish", d, h
    if d == "sell" and h != "buy":
        return "bearish", d, h
    return "neutral", d, h


def analyze_intraday(pair, candles, min_rr=None, require_killzone=True,
                     min_sweep_atr=MIN_SWEEP_ATR, min_disp_body_atr=MIN_DISP_BODY_ATR,
                     equal_pools_only=EQUAL_POOLS_ONLY,
                     htf_bias=None, tf="15min", draw_targets=None):
    """Return one sweep-reversal signal dict, or None if no disciplined setup.

    Top-down (set by the service): htf_bias 'bullish' -> longs only, 'bearish' ->
    shorts only, 'neutral' -> stand aside (None); None = no HTF filter (back-compat).
    tf = entry timeframe label (e.g. '5min' / '15min'). draw_targets = HTF draw-on-
    liquidity prices (prev day/week H-L) the TP prefers over local structure pools.

    Quality filters (defaults are the tuned module values; the backtester sweeps them):
      min_sweep_atr     — sweep must penetrate the level by >= this * ATR (a real raid,
                          not a 1-pip poke)
      min_disp_body_atr — the MSS-breaking candle body must be >= this * ATR (true
                          displacement, not a drift over the swing)
      equal_pools_only  — only sweep engineered equal-highs/lows (drop lone swings)
    """
    if not candles or len(candles) < MIN_CANDLES:
        return None
    min_rr = INTRADAY_MIN_RR if min_rr is None else min_rr

    pip = _pip(pair)
    atr = _atr(candles)
    sl_buffer = max(atr * 0.5, pip * 5)  # tight intraday buffer beyond the wick
    ts_index = {c["datetime"]: i for i, c in enumerate(candles)}

    swings = detect_swings(candles, lookback=SWING_LOOKBACK)
    swing_highs, swing_lows = swings["swing_highs"], swings["swing_lows"]
    equal_highs = detect_equal_highs(swing_highs)
    equal_lows = detect_equal_lows(swing_lows)

    # Liquidity zones: engineered equal-highs/lows, plus (unless equal_pools_only)
    # every swing extreme as a resting pool.
    sell_zones = list(equal_lows)
    buy_zones = list(equal_highs)
    if not equal_pools_only:
        sell_zones += [{"price": s["price"], "first_touch": s["timestamp"]} for s in swing_lows]
        buy_zones += [{"price": s["price"], "first_touch": s["timestamp"]} for s in swing_highs]

    sell_sweeps = detect_sell_side_sweeps(candles, sell_zones)   # -> long bias
    buy_sweeps  = detect_buy_side_sweeps(candles, buy_zones)     # -> short bias

    # Top-down hard filter: only trade in the HTF direction; stand aside if neutral.
    if htf_bias == "neutral":
        return None
    allow_long = htf_bias in (None, "bullish")
    allow_short = htf_bias in (None, "bearish")

    longs = _long_setup(pair, candles, sell_sweeps, swing_highs, equal_highs,
                        ts_index, pip, atr, sl_buffer, min_rr, require_killzone,
                        min_sweep_atr, min_disp_body_atr, tf, draw_targets, htf_bias) if allow_long else None
    shorts = _short_setup(pair, candles, buy_sweeps, swing_lows, equal_lows,
                         ts_index, pip, atr, sl_buffer, min_rr, require_killzone,
                         min_sweep_atr, min_disp_body_atr, tf, draw_targets, htf_bias) if allow_short else None

    candidates = [s for s in (longs, shorts) if s]
    if not candidates:
        return None
    # If both fire (rare), take the higher-quality one.
    return max(candidates, key=lambda s: s["quality_score"])


# ── LONG: sell-side sweep -> bullish displacement/MSS -> buy the FVG/OTE ──────
def _long_setup(pair, candles, sweeps, swing_highs, equal_highs,
                ts_index, pip, atr, sl_buffer, min_rr, require_killzone,
                min_sweep_atr=0.0, min_disp_body_atr=0.0,
                tf="15min", draw_targets=None, htf_bias=None):
    n = len(candles)
    last_close = candles[-1]["close"]

    recent = [s for s in sweeps if ts_index.get(s["timestamp"], -1) >= n - RECENT_BARS]
    if not recent:
        return None
    sweep = max(recent, key=lambda s: ts_index.get(s["timestamp"], -1))
    sweep_idx = ts_index.get(sweep["timestamp"], -1)
    if sweep_idx < 2 or sweep_idx >= n - 1:
        return None
    sweep_low = candles[sweep_idx]["low"]

    # Real raid: the sweep must penetrate the level by a minimum depth.
    if min_sweep_atr > 0 and (sweep["price"] - sweep_low) < min_sweep_atr * atr:
        return None

    kz = in_killzone(candles[sweep_idx]["datetime"])
    if require_killzone and not kz.get("entry_allowed"):
        return None

    pre_highs = [h for h in swing_highs if h["index"] <= sweep_idx]
    if not pre_highs:
        return None
    ref_price = max(pre_highs, key=lambda h: h["index"])["price"]

    mss_idx = next((j for j in range(sweep_idx + 1, n) if candles[j]["close"] > ref_price), None)
    if mss_idx is None or mss_idx < n - RECENT_AFTER:
        return None

    disp_high = max(c["high"] for c in candles[sweep_idx:mss_idx + 1])
    leg = disp_high - sweep_low
    if leg < DISPLACEMENT_ATR * atr:
        return None
    if not any((candles[j]["close"] - candles[j]["open"]) >= STRONG_BODY_ATR * atr
               for j in range(sweep_idx + 1, mss_idx + 1)):
        return None
    # True displacement: the candle that broke structure is itself a strong body.
    if min_disp_body_atr > 0 and (candles[mss_idx]["close"] - candles[mss_idx]["open"]) < min_disp_body_atr * atr:
        return None

    entry, used_fvg = _long_entry(candles, sweep_idx, mss_idx, sweep_low, disp_high)
    sl = sweep_low - sl_buffer
    if entry <= sl:
        return None
    risk = entry - sl

    tp, tp_is_draw = _target_above(swing_highs, equal_highs, entry + min_rr * risk, draw_targets)
    if tp is None or not (sl < last_close < tp):
        return None
    rr = (tp - entry) / risk
    if rr < min_rr:
        return None

    return _build(pair, "BUY", entry, sl, tp, rr, last_close, pip, kz,
                  sweep, ref_price, used_fvg, atr, tf, htf_bias, tp_is_draw)


# ── SHORT: buy-side sweep -> bearish displacement/MSS -> sell the FVG/OTE ─────
def _short_setup(pair, candles, sweeps, swing_lows, equal_lows,
                 ts_index, pip, atr, sl_buffer, min_rr, require_killzone,
                 min_sweep_atr=0.0, min_disp_body_atr=0.0,
                 tf="15min", draw_targets=None, htf_bias=None):
    n = len(candles)
    last_close = candles[-1]["close"]

    recent = [s for s in sweeps if ts_index.get(s["timestamp"], -1) >= n - RECENT_BARS]
    if not recent:
        return None
    sweep = max(recent, key=lambda s: ts_index.get(s["timestamp"], -1))
    sweep_idx = ts_index.get(sweep["timestamp"], -1)
    if sweep_idx < 2 or sweep_idx >= n - 1:
        return None
    sweep_high = candles[sweep_idx]["high"]

    # Real raid: the sweep must penetrate the level by a minimum depth.
    if min_sweep_atr > 0 and (sweep_high - sweep["price"]) < min_sweep_atr * atr:
        return None

    kz = in_killzone(candles[sweep_idx]["datetime"])
    if require_killzone and not kz.get("entry_allowed"):
        return None

    pre_lows = [l for l in swing_lows if l["index"] <= sweep_idx]
    if not pre_lows:
        return None
    ref_price = max(pre_lows, key=lambda l: l["index"])["price"]

    mss_idx = next((j for j in range(sweep_idx + 1, n) if candles[j]["close"] < ref_price), None)
    if mss_idx is None or mss_idx < n - RECENT_AFTER:
        return None

    disp_low = min(c["low"] for c in candles[sweep_idx:mss_idx + 1])
    leg = sweep_high - disp_low
    if leg < DISPLACEMENT_ATR * atr:
        return None
    if not any((candles[j]["open"] - candles[j]["close"]) >= STRONG_BODY_ATR * atr
               for j in range(sweep_idx + 1, mss_idx + 1)):
        return None
    # True displacement: the candle that broke structure is itself a strong body.
    if min_disp_body_atr > 0 and (candles[mss_idx]["open"] - candles[mss_idx]["close"]) < min_disp_body_atr * atr:
        return None

    entry, used_fvg = _short_entry(candles, sweep_idx, mss_idx, sweep_high, disp_low)
    sl = sweep_high + sl_buffer
    if entry >= sl:
        return None
    risk = sl - entry

    tp, tp_is_draw = _target_below(swing_lows, equal_lows, entry - min_rr * risk, draw_targets)
    if tp is None or not (tp < last_close < sl):
        return None
    rr = (entry - tp) / risk
    if rr < min_rr:
        return None

    return _build(pair, "SELL", entry, sl, tp, rr, last_close, pip, kz,
                  sweep, ref_price, used_fvg, atr, tf, htf_bias, tp_is_draw)


# ── Entry helpers ───────────────────────────────────────────────────────────
def _long_entry(candles, sweep_idx, mss_idx, sweep_low, disp_high):
    """Bullish FVG left by the displacement, else OTE 70.5% retrace of the leg."""
    fvgs = detect_fvg(candles)["bullish_fvg_zones"]
    cand = [f for f in fvgs if sweep_idx < f["index"] <= mss_idx + 2]
    if cand:
        f = max(cand, key=lambda x: x["index"])
        mid = (f["start"] + f["end"]) / 2.0
        return min(max(mid, sweep_low), disp_high), True
    return disp_high - 0.705 * (disp_high - sweep_low), False


def _short_entry(candles, sweep_idx, mss_idx, sweep_high, disp_low):
    """Bearish FVG left by the displacement, else OTE 70.5% retrace of the leg."""
    fvgs = detect_fvg(candles)["bearish_fvg_zones"]
    cand = [f for f in fvgs if sweep_idx < f["index"] <= mss_idx + 2]
    if cand:
        f = max(cand, key=lambda x: x["index"])
        mid = (f["start"] + f["end"]) / 2.0
        return max(min(mid, sweep_high), disp_low), True
    return disp_low + 0.705 * (sweep_high - disp_low), False


def _target_above(swing_highs, equal_highs, floor, draws=None):
    """TP for a long = the NEAREST opposing liquidity at/above `floor` (the min-RR
    threshold), whether a structural pool or an HTF draw. Taking the nearest keeps
    RR realistic (a far weekly draw is the runner target, reported separately, not
    the primary TP). Returns (price, is_draw)."""
    pools = [h["price"] for h in swing_highs if h["price"] >= floor] + \
            [e["price"] for e in equal_highs if e["price"] >= floor]
    draw_hits = [d for d in (draws or []) if d >= floor]
    cands = pools + draw_hits
    if not cands:
        return None, False
    tp = min(cands)
    return tp, any(abs(tp - d) < 1e-9 for d in draw_hits)


def _target_below(swing_lows, equal_lows, ceil, draws=None):
    """TP for a short = the NEAREST opposing liquidity at/below `ceil` (pool or HTF
    draw). Nearest keeps RR realistic. Returns (price, is_draw)."""
    pools = [l["price"] for l in swing_lows if l["price"] <= ceil] + \
            [e["price"] for e in equal_lows if e["price"] <= ceil]
    draw_hits = [d for d in (draws or []) if d <= ceil]
    cands = pools + draw_hits
    if not cands:
        return None, False
    tp = max(cands)
    return tp, any(abs(tp - d) < 1e-9 for d in draw_hits)


# ── Signal assembly ─────────────────────────────────────────────────────────
def _quality(kz, used_fvg, rr):
    score = 55
    if kz.get("entry_allowed"):
        score += 20
    if used_fvg:
        score += 15
    score += min(int(max(rr - 2.0, 0) * 5), 10)
    return min(score, 100)


def _reason(side, kz, used_fvg, tf="15min", htf_bias=None, tp_is_draw=False):
    word = "Sell-side" if side == "BUY" else "Buy-side"
    rev = "bullish" if side == "BUY" else "bearish"
    basis = "FVG" if used_fvg else "OTE 70.5% retrace"
    tgt = "the HTF draw on liquidity" if tp_is_draw else "the next opposite liquidity pool"
    bias_txt = f"In HTF {htf_bias} bias: " if htf_bias else ""
    return (f"{bias_txt}{word} liquidity sweep ({tf}) in {kz.get('killzone')} killzone, "
            f"{rev} displacement breaking structure (MSS). Entry at {basis}; "
            f"SL beyond the sweep wick; TP at {tgt}.")


def _build(pair, side, entry, sl, tp, rr, last_close, pip, kz, sweep, ref_price, used_fvg, atr,
           tf="15min", htf_bias=None, tp_is_draw=False):
    entry, sl, tp = _round(entry, pair), _round(sl, pair), _round(tp, pair)
    dist = abs(last_close - entry) / pip
    return {
        "pair": pair,
        "signal": side,
        "timeframe": tf,
        "model": "Intraday Liquidity Sweep",
        "entry": entry,
        "stop_loss": sl,
        "take_profit": tp,
        "current_price": _round(last_close, pair),
        "entry_type": "market" if dist <= 2 else "limit",
        "distance_to_entry_pips": round(dist, 1),
        "risk_reward": round(rr, 2),
        "quality_score": _quality(kz, used_fvg, rr),
        "killzone": kz.get("killzone"),
        "session": kz.get("killzone"),
        "htf_bias": htf_bias,
        "swept_liquidity": _round(sweep["price"], pair),
        "sweep_time": sweep["timestamp"],
        "mss_level": _round(ref_price, pair),
        "entry_basis": "FVG" if used_fvg else "OTE 70.5%",
        "target_basis": "HTF draw on liquidity" if tp_is_draw else "structure pool",
        "setup": _reason(side, kz, used_fvg, tf, htf_bias, tp_is_draw),
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
