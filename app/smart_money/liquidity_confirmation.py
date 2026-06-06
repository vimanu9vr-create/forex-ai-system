def confirm_liquidity_grab(
        sweeps,
        choch,
        killzone,
        multi_timeframe
):
    
    if (
        sweeps["swept"]
        and choch["choch"]
        and killzone["active"]
        and multi_timeframe["valid"]
    ):
        return {
            "liquidity_grab_confirmed": True,
            "reason": "All conditions for liquidity grab are met: sweeps detected, choch confirmed, price in killzone, and multi-timeframe alignment."
        }
    
    return {
        "liquidity_grab_confirmed": False,
        "reason": "Not all conditions for liquidity grab are met."
    }