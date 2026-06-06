def analyze_multi_timeframe(
        higher_timeframe_bias,
        lower_timeframe_setup
):
    if not lower_timeframe_setup:
        return{
            "aligned": False,
            "reason": "No valid setup on lower timeframe"
        }
    
    setup_type = lower_timeframe_setup[0]["type"]
    setup_confidence = lower_timeframe_setup[0]["confidence"]

    if (
        higher_timeframe_bias == "bullish" and
        setup_type == "buy" and
        setup_confidence >= 80
    ):
        return {
            "aligned": True,
            "direction": "buy",
            "reason": "Higher timeframe bullish bias aligns with strong buy setup on lower timeframe"
        }
    
    if(
        higher_timeframe_bias == "bearish" and
        setup_type == "sell" and
        setup_confidence >= 80
    ):
        return {
            "aligned": True,
            "direction": "sell",
            "reason": "Higher timeframe bearish bias aligns with strong sell setup on lower timeframe"
        }
    
    return {
        "aligned": False,
        "reason": "Higher timeframe bias does not align with lower timeframe setup"
    }