def sniper_entry(
        probability,
        liquidity_confirmation,
        premium_discount

):
    if (
        probability["score"] >= 80
        and liquidity_confirmation["liquidity_grab_confirmed"]
        and premium_discount["favorable"]
    ):
        return {
            "sniper_entry": True,
            "reason": "All conditions for sniper entry are met: high probability, liquidity grab confirmed, and favorable premium/discount."
        }
    
    return {
        "sniper_entry": False,
        "reason": "Not all conditions for sniper entry are met."
    }