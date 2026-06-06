
def generate_live_signal(
        sniper_entry,
        probability,
        killzone
):
    # safe checks using .get() and tolerant parsing
    sniper_ok = False
    if isinstance(sniper_entry, dict):
        sniper_ok = bool(sniper_entry.get("sniper_entry"))
    else:
        sniper_ok = bool(sniper_entry)

    if not sniper_ok:
        return {"live_signal": False, "reason": "Sniper entry conditions not met."}

    score = 0
    if isinstance(probability, dict):
        score = int(probability.get("score", 0))

    if score < 80:
        return {"live_signal": False, "reason": "Probability score below threshold."}

    if not (isinstance(killzone, dict) and killzone.get("active")):
        return {"live_signal": False, "reason": "Price not in killzone."}

    # handle possible key with/without trailing space and normalize
    direction = None
    if isinstance(sniper_entry, dict):
        direction = sniper_entry.get("direction") or sniper_entry.get("direction ")
    if isinstance(direction, str):
        direction = direction.strip().lower()

    if direction == "long":
        return {
            "live_signal": True,
            "reason": "Conditions for long live signal are met.",
            "confidence": "High",
            "probability_score": score,
            "killzone_status": "Active"
        }
    elif direction == "short":
        return {
            "live_signal": True,
            "reason": "Conditions for short live signal are met.",
            "confidence": "High",
            "probability_score": score,
            "killzone_status": "Active"
        }

    return {"live_signal": False, "reason": "Waiting for direction confirmation."}