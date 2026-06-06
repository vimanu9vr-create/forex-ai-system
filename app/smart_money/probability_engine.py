
def calculate_probability (
        sweeps,
        choch,
        killzone,
        multi_timeframe,
        fvg,
        order_blocks
):

    score = 0
    reasons = []

    if sweeps["swept"]:
        score += 20
        reasons.append("Sweeps detected")

    if choch["choch"]:
        score += 20
        reasons.append("CHOCH confirmed")

    if killzone["active"]:
        score += 20
        reasons.append("Price in killzone")

    if multi_timeframe["valid"]:
        score += 20
        reasons.append("Multi-timeframe alignment")

    if fvg["present"]:
        score += 10
        reasons.append("FVG zones detected")

    if order_blocks["present"]:
        score += 10
        reasons.append("Order blocks detected")

    if score >= 80:
        reasons.append("High probability of successful trade setup")
    elif score >= 50:
        reasons.append("Moderate probability of successful trade setup")
    else:
        reasons.append("Low probability of successful trade setup")

    return {
        "probability_score": score,
        "reasons": reasons
    }