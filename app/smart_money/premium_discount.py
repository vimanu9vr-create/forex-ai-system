def calculate_premium_discount(
        swing_highs,
        swing_lows,
        current_price
):
    
    equilibrium_price = (swing_highs[-1] + swing_lows[-1]) / 2
   
    if current_price > equilibrium_price:
        zone = "premium"

    elif current_price < equilibrium_price:
        zone = "discount"

    else:
        zone = "equilibrium"

    return {
        "swing_highs": swing_highs,
        "swing_lows": swing_lows,
        "current_price": current_price,
        "equilibrium_price": equilibrium_price,
        "zone": zone
    }