def format_twelvedata_data(raw_data):


    candles =[]

    values =raw_data.get("values", [])

    for item in values:

        candles.append({
            "timestamp":item["datetime"],
            "open":float(item["open"]),
            "high":float(item["high"]),
            "low":float(item["low"]),
            "close":float(item["close"])
        })
            
        return candles