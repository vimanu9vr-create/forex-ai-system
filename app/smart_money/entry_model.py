def entry_model(
        sweeps,
        choch,
        fvg,
        bias    
):
    
    setups =[]

    bullish_sweep =any(
        sweep["type"] == "buy_side_sweep" for sweep in sweeps
    )

    bullish_choch = any(
        item.get("type") == "bullish_choch" for item in choch
    )

    bullish_fvg = len(
        fvg["bullish_fvg_zones"]
    ) > 0

    if (
        bias["bias"] == "bullish" and
        bullish_sweep and
        bullish_choch and
        bullish_fvg
    ):
        setups.append({
            "type": "buy",
            "confidence": 85,
            "reason":(
                "bullish sweep + "
                "bullish CHOCH + "
                "bullish FVG"
                "bullish bias"

            )
        })
    
    bearish_sweep = any(
        sweep["type"] == "sell_side_sweep" for sweep in sweeps )
    
    bearish_choch = any(
        item.get("type") == "bearish_choch" for item in choch)
    
    bearish_fvg = len(
        fvg["bearish_fvg_zones"]
    ) > 0

    if (
        bias["bias"] == "bearish" and
        bearish_sweep and
        bearish_choch and
        bearish_fvg
    ):
        setups.append({
            "type": "sell",
            "confidence": 85,
            "reason":(
                "bearish sweep + "
                "bearish CHOCH + "
                "bearish FVG"
                "bearish bias"

            )
        })
    return setups