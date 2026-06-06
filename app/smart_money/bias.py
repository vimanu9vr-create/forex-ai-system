def determine_market_bias(
        bullish_bos: list,
        bearish_bos: list,
        bullish_choch: list,
        bearish_choch: list

):
    
    bullish_score = 0
    bearish_score = 0

    bullish_score += len(bullish_bos) * 2
    bullish_score += len(bullish_choch) * 3
    bearish_score += len(bearish_bos) * 2
    bearish_score += len(bearish_choch) * 3

    # Canonical bias value is lowercase ("bullish"/"bearish"/"neutral") — every
    # consumer (setups, entry_model, multi_timeframe, crew tools, agents) keys
    # off lowercase. Display layers uppercase/title-case as needed.
    if bullish_score > bearish_score:
        bias = "bullish"
    elif bearish_score > bullish_score:
        bias = "bearish"
    else:
        bias = "neutral"

    return {
        "bias": bias,
        "bullish_score": bullish_score,
        "bearish_score": bearish_score,
    }


def compute_market_bias(pair: str = "EURUSD", interval: str = "1h") -> dict:
    """
    Compute the real market bias for a pair from smart-money structure
    (BOS + CHoCH) and score it via determine_market_bias().

    Returns the determine_market_bias() shape plus the pair:
        {"bias": "Bullish"|"Bearish"|"Neutral",
         "bullish_score": int, "bearish_score": int, "pair": str}

    Falls back to Neutral if candle data is unavailable so callers
    (e.g. the dashboard) never break on a data/network hiccup.
    """
    from app.services.market_data import get_forex_intraday
    from app.smart_money.structure import detect_swings
    from app.smart_money.bos import detect_bullish_bos, detect_bearish_bos
    from app.smart_money.choch import detect_bullish_choch, detect_bearish_choch

    candles = get_forex_intraday(pair, interval=interval)
    if not candles:
        return {"bias": "neutral", "bullish_score": 0, "bearish_score": 0,
                "pair": pair, "note": "no candle data"}

    swings = detect_swings(candles)

    bullish_bos = detect_bullish_bos(candles, swings["swing_highs"])
    bearish_bos = detect_bearish_bos(candles, swings["swing_lows"])
    bullish_choch = detect_bullish_choch(candles, swings["swing_highs"])
    bearish_choch = detect_bearish_choch(candles, swings["swing_lows"])

    result = determine_market_bias(
        bullish_bos=bullish_bos,
        bearish_bos=bearish_bos,
        bullish_choch=bullish_choch,
        bearish_choch=bearish_choch,
    )
    result["pair"] = pair
    return result