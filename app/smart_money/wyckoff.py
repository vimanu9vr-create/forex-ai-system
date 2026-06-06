"""
Wyckoff phase engine — simplified accumulation / distribution detection.

Reads a recent trading range from price structure and classifies it, using
tick-volume (from Polygon) to confirm effort-vs-result when available:

  - Spring   : price dips below range support then closes back inside
               (sell-side liquidity grab) → accumulation / bullish.
  - Upthrust : price spikes above range resistance then closes back inside
               (buy-side liquidity grab) → distribution / bearish.
  - Phase    : inferred from the move INTO the range (down → accumulation
               context, up → distribution context) plus spring/upthrust events.
  - Volume   : each event is tagged with its volume vs the range average
               (effort); a spring on high volume / test on low volume is the
               textbook Wyckoff confirmation.

This is a pragmatic heuristic, not a full Wyckoff schematic — good for a phase
+ bias read to feed the desk analysis, not a substitute for discretionary study.
"""


def _digits(pair: str) -> int:
    return 3 if "JPY" in pair.upper() else 5


def detect_wyckoff(candles, pair: str = "EURUSD", range_window: int = 40) -> dict:
    d = _digits(pair)
    if not candles or len(candles) < range_window + 10:
        return {"phase": "insufficient data", "bias": "neutral", "events": []}

    window = candles[-range_window:]
    split = max(5, int(range_window * 0.7))
    established = window[:split]          # the range that got built
    recent = window[split:]              # where springs/upthrusts show up

    support = min(c["low"] for c in established)
    resistance = max(c["high"] for c in established)
    if resistance <= support:
        return {"phase": "flat", "bias": "neutral", "events": []}

    vols = [c.get("volume", 0) or 0 for c in window]
    avg_vol = sum(vols) / len(vols) if vols else 0

    # Trend INTO the range: down → accumulation context, up → distribution context.
    prior = candles[-(range_window + 30):-range_window] if len(candles) >= range_window + 30 else []
    prior_avg = sum(c["close"] for c in prior) / len(prior) if prior else (support + resistance) / 2
    came_down = prior_avg > resistance
    came_up = prior_avg < support

    events, spring, upthrust = [], False, False
    for c in recent:
        v = c.get("volume", 0) or 0
        vx = round(v / avg_vol, 2) if avg_vol else None
        if c["low"] < support and c["close"] > support:
            spring = True
            events.append({"event": "Spring", "price": round(c["low"], d), "volume_vs_avg": vx})
        if c["high"] > resistance and c["close"] < resistance:
            upthrust = True
            events.append({"event": "Upthrust", "price": round(c["high"], d), "volume_vs_avg": vx})

    if spring and not upthrust:
        phase, bias = "Accumulation — spring reclaimed the range low (markup likely)", "bullish"
    elif upthrust and not spring:
        phase, bias = "Distribution — upthrust rejected the range high (markdown likely)", "bearish"
    elif came_down:
        phase, bias = "Possible accumulation — consolidation after a decline", "bullish"
    elif came_up:
        phase, bias = "Possible distribution — consolidation after an advance", "bearish"
    else:
        phase, bias = "Ranging — no clear Wyckoff bias", "neutral"

    return {
        "phase": phase,
        "bias": bias,
        "range": {"support": round(support, d), "resistance": round(resistance, d)},
        "events": events[-4:],
        "volume_confirmed": avg_vol > 0,
        "note": ("effort-vs-result via real tick-volume" if avg_vol > 0
                 else "price-action only (no volume)"),
    }
