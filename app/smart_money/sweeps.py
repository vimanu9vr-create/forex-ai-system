def detect_buy_side_sweeps(
    candles,
    liquidity_zones,
):
    """
    Buy-side sweep: price wicks ABOVE a buy-side liquidity level then closes back
    below it (a stop-hunt above equal highs).

    One sweep per zone — the first candle to sweep it, and only candles after the
    zone formed (time-ordered). Prevents a single level from being counted once
    per touching candle (which produced hundreds of duplicate sweeps).
    """
    sweeps = []

    for zone in liquidity_zones:

        liquidity_price = zone["price"]
        formed_at = zone.get("second_touch") or zone.get("first_touch") or ""

        for candle in candles:

            if formed_at and candle["datetime"] <= formed_at:
                continue

            swept = (
                candle["high"] > liquidity_price and
                candle["close"] < liquidity_price
            )

            if swept:
                sweeps.append({
                    "price": liquidity_price,
                    "timestamp": candle["datetime"],
                    "type": "buy_side_sweep"
                })
                break  # first sweep per zone

    return sweeps


def detect_sell_side_sweeps(
    candles,
    liquidity_zones,
):
    """
    Sell-side sweep: price wicks BELOW a sell-side liquidity level then closes back
    above it (a stop-hunt below equal lows).

    One sweep per zone — the first candle to sweep it, after the zone formed.
    """
    sweeps = []

    for zone in liquidity_zones:

        liquidity_price = zone["price"]
        formed_at = zone.get("second_touch") or zone.get("first_touch") or ""

        for candle in candles:

            if formed_at and candle["datetime"] <= formed_at:
                continue

            swept = (
                candle["low"] < liquidity_price and
                candle["close"] > liquidity_price
            )

            if swept:
                sweeps.append({
                    "price": liquidity_price,
                    "timestamp": candle["datetime"],
                    "type": "sell_side_sweep"
                })
                break  # first sweep per zone

    return sweeps
