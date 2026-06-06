def detect_swings(
    candles,
    lookback=1
):

    swing_highs = []
    swing_lows = []

    for i in range(
        lookback,
        len(candles) - lookback
    ):

        current_candle = candles[i]

        current_high = current_candle["high"]
        current_low = current_candle["low"]

        previous_candles = candles[
            i - lookback:i
        ]

        next_candles = candles[
            i + 1:i + lookback + 1
        ]

        is_swing_high = all(
            current_high > candle["high"]
            for candle in previous_candles
        ) and all(
            current_high > candle["high"]
            for candle in next_candles
        )

        is_swing_low = all(
            current_low < candle["low"]
            for candle in previous_candles
        ) and all(
            current_low < candle["low"]
            for candle in next_candles
        )

        if is_swing_high:

            swing_highs.append({
                "index": i,
                "timestamp": current_candle["datetime"],
                "price": current_high
            })

        if is_swing_low:

            swing_lows.append({
                "index": i,
                "timestamp": current_candle["datetime"],
                "price": current_low
            })

    return {
        "swing_highs": swing_highs,
        "swing_lows": swing_lows
    }