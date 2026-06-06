def detect_order_blocks(
        candles
):
    
    bullish_order_blocks =[]
    bearsih_order_blocks = []

    for i in range (1, len(candles)-1):

        curent_candle = candles[i]

        next_candle = candles[i+1]

        # Check for bullish order block
        if (
            curent_candle["close"] < curent_candle["open"] and
            next_candle["close"] > next_candle["open"] and
            next_candle["close"] > curent_candle["open"]
        ):
            bullish_order_blocks.append({
                "type": "bullish",
                "start": curent_candle["open"],
                "end": curent_candle["close"],
                "index": i,
                "timestamp": curent_candle["datetime"]
            })
   
     # Check for bearish order block
        elif (
            curent_candle["close"] > curent_candle["open"] and
            next_candle["close"] < next_candle["open"] and
            next_candle["close"] < curent_candle["open"]
        ):
            bearsih_order_blocks.append({
                "type": "bearish",
                "start": curent_candle["open"],
                "end": curent_candle["close"],
                "index": i,
                "timestamp": curent_candle["datetime"] 
            })  
    
    return {
        "bullish_order_blocks": bullish_order_blocks,
        "bearish_order_blocks": bearsih_order_blocks
    }