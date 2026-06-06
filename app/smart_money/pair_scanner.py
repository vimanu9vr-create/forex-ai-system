def scan_pairs ():
    pairs = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]
    scanned_pairs = []
    for pair in pairs:
       
       if pair == "EURUSD":
         scanned_pairs.append({
            "pair": pair,
            "signal": "buy",
                "confidence": 85,
                "probability_score": 85
            })
       elif pair == "GBPUSD":
         scanned_pairs.append({
            "pair": pair,
            "signal": "sell",
                "confidence": 80,
                "probability_score": 80
            })
       elif pair == "USDJPY":
         scanned_pairs.append({
            "pair": pair,
            "signal": "buy",
                "confidence": 75,
                "probability_score": 75
            })
       elif pair == "AUDUSD":
         scanned_pairs.append({
            "pair": pair,
            "signal": "sell",
                "confidence": 70,
                "probability_score": 70
            })
       elif pair == "USDCAD":
         scanned_pairs.append({
            "pair": pair,
            "signal": "buy",
                "confidence": 65,
                "probability_score": 65
            })
         
         best_pair = max(scanned_pairs, key=lambda x: x["confidence"])
    return {
      "best_pair": best_pair,
      "all_scanned_pairs": scanned_pairs
    }
