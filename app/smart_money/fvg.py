def detect_fvg(candles):
    bullish_fvg_zones = []
    bearish_fvg_zones = []
    for i in range(2, len(candles)):
        current_candle = candles[i]
        previous_candle = candles[i - 1]
        pre_previous_candle = candles[i - 2]

        # Check for bullish FVG
        if (
            current_candle["low"] > previous_candle["high"] and
            previous_candle["low"] > pre_previous_candle["high"]
        ):
            bullish_fvg_zones.append({
                "type": "bullish",
                "start": pre_previous_candle["high"],
                "end": previous_candle["low"],
                "index": i
            })

        # Check for bearish FVG
        elif (
            current_candle["high"] < previous_candle["low"] and
            previous_candle["high"] < pre_previous_candle["low"]
        ):
            bearish_fvg_zones.append({
                "type": "bearish",
                "start": pre_previous_candle["low"],
                "end": previous_candle["high"],
                "index": i
            })

    return {
        "bullish_fvg_zones": bullish_fvg_zones,
        "bearish_fvg_zones": bearish_fvg_zones
    }