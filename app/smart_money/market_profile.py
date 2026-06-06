"""
Price profile — Volume Profile when tick-volume is available, else Market
Profile (TPO / time-at-price).

Polygon supplies real forex tick-volume, so when candles carry a "volume" field
this builds a true volume-at-price distribution; with OHLC-only data it falls
back to TPO (counting time-at-price). Either way it yields the same decision
levels:

  - POC (Point of Control): the price level with the most activity
  - Value Area (VAH / VAL): the band around POC holding ~70% of activity
  - HVN / LVN: high- and low-activity nodes (acceptance vs rejection zones)
"""


def _digits(pair: str) -> int:
    return 3 if "JPY" in pair.upper() else 5


def build_market_profile(candles, pair="EURUSD", rows: int = 50,
                         value_area_pct: float = 0.70) -> dict:
    """
    Returns {poc, vah, val, value_area_pct, profile, hvn, lvn, method} or {} if
    there isn't enough data. `profile` is a list of {price, count} buckets.
    """
    if not candles or len(candles) < 10:
        return {}

    hi = max(c["high"] for c in candles)
    lo = min(c["low"] for c in candles)
    if hi <= lo:
        return {}

    rows = max(10, int(rows))
    step = (hi - lo) / rows

    def bucket(price: float) -> int:
        return min(int((price - lo) / step), rows - 1)

    def price_at(b: int) -> float:
        return lo + (b + 0.5) * step

    # Distribute each candle across the price buckets it spans: real tick-volume
    # when present (true volume profile), else +1 per bucket (TPO).
    counts = [0.0] * rows
    used_volume = False
    for c in candles:
        b_lo, b_hi = bucket(c["low"]), bucket(c["high"])
        span = b_hi - b_lo + 1
        vol = c.get("volume") or 0
        if vol > 0:
            used_volume = True
            w = vol / span
        else:
            w = 1.0
        for b in range(b_lo, b_hi + 1):
            counts[b] += w

    total = sum(counts)
    if total <= 0:
        return {}

    poc_idx = max(range(rows), key=lambda b: counts[b])

    # Value area: expand out from POC, adding the heavier adjacent bucket, until
    # the included activity reaches value_area_pct of the total.
    lo_i = hi_i = poc_idx
    acc = counts[poc_idx]
    target = value_area_pct * total
    while acc < target and (lo_i > 0 or hi_i < rows - 1):
        left = counts[lo_i - 1] if lo_i > 0 else -1
        right = counts[hi_i + 1] if hi_i < rows - 1 else -1
        if right >= left:
            hi_i += 1
            acc += counts[hi_i]
        else:
            lo_i -= 1
            acc += counts[lo_i]

    digits = _digits(pair)
    avg = total / rows
    profile = [{"price": round(price_at(b), digits), "count": round(counts[b], 1)} for b in range(rows)]

    return {
        "poc": round(price_at(poc_idx), digits),
        "vah": round(price_at(hi_i), digits),
        "val": round(price_at(lo_i), digits),
        "value_area_pct": value_area_pct,
        "profile": profile,
        "hvn": sorted([p for p in profile if p["count"] >= avg * 1.5],
                      key=lambda x: -x["count"])[:5],
        "lvn": [p for p in profile if 0 < p["count"] <= avg * 0.5][:5],
        "method": ("Volume Profile (real tick-volume)" if used_volume
                   else "TPO (time-at-price; volume-independent)"),
    }
