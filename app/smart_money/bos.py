def detect_bullish_bos(candles, swing_highs):
    """
    Bullish Break of Structure: price closes above a prior swing high.

    One signal per swing — the FIRST candle to break it, and only candles
    that occur after the swing formed (time-ordered). This prevents a single
    break from being counted once per subsequent candle.
    """
    bos_signals = []

    for swing in swing_highs:
        swing_price = swing["price"]
        swing_ts = swing["timestamp"]

        for candle in candles:
            if candle["datetime"] <= swing_ts:
                continue
            if candle["high"] > swing_price and candle["close"] > swing_price:
                bos_signals.append({
                    "price": swing_price,
                    "timestamp": candle["datetime"],
                    "type": "bullish_bos",
                    "close": candle["close"],
                })
                break  # first break only — one BOS per swing

    return bos_signals


def detect_bearish_bos(candles, swing_lows):
    """
    Bearish Break of Structure: price closes below a prior swing low.

    One signal per swing — the FIRST candle to break it, after it formed.
    """
    bos_signals = []

    for swing in swing_lows:
        swing_price = swing["price"]
        swing_ts = swing["timestamp"]

        for candle in candles:
            if candle["datetime"] <= swing_ts:
                continue
            if candle["low"] < swing_price and candle["close"] < swing_price:
                bos_signals.append({
                    "price": swing_price,
                    "timestamp": candle["datetime"],
                    "type": "bearish_bos",
                    "close": candle["close"],
                })
                break  # first break only — one BOS per swing

    return bos_signals
