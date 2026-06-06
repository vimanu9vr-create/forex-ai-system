"""
Change of Character (CHoCH) — the FIRST break of the most recent swing,
signalling a potential shift in market character (i.e. a reversal).

A CHoCH is reported only for the latest swing high / swing low, so there is
at most one bullish and one bearish CHoCH — representing the most recent
change of character. This replaces the previous logic, which flagged every
candle that closed beyond *any* swing (with no time ordering) and therefore
produced hundreds of meaningless signals.
"""


def detect_bullish_choch(candles, swing_highs):
    """Bullish CHoCH: first candle to close above the most recent swing high."""
    if not swing_highs:
        return []

    swing = swing_highs[-1]            # most recent swing high
    swing_price = swing["price"]
    swing_ts = swing["timestamp"]

    for candle in candles:
        if candle["datetime"] <= swing_ts:
            continue
        if candle["close"] > swing_price:
            return [{
                "type": "bullish_choch",
                "broken_level": swing_price,
                "timestamp": candle["datetime"],
                "close": candle["close"],
            }]

    return []


def detect_bearish_choch(candles, swing_lows):
    """Bearish CHoCH: first candle to close below the most recent swing low."""
    if not swing_lows:
        return []

    swing = swing_lows[-1]             # most recent swing low
    swing_price = swing["price"]
    swing_ts = swing["timestamp"]

    for candle in candles:
        if candle["datetime"] <= swing_ts:
            continue
        if candle["close"] < swing_price:
            return [{
                "type": "bearish_choch",
                "broken_level": swing_price,
                "timestamp": candle["datetime"],
                "close": candle["close"],
            }]

    return []
