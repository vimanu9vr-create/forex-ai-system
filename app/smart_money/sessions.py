from datetime import datetime

def detect_session():
    now = datetime.utcnow()
    current_hour = now.hour
    current_minute = now.minute

    # market close: 00:00 - 00:30 UTC
    if current_hour == 0 and current_minute < 30:
        return {
            "session": "Market Close",
            "volatility": "Very Low",
            "trading_style": "No Trading"
        }

    # ASIA SESSION: 00:30 - 08:00 UTC
    if 0 <= current_hour < 8:
        return {
            "session": "Asia",
            "volatility": "Low",
            "trading_style": "Range Trading"
        }
    # London session: 08:00 - 16:00 UTC
    elif 8 <= current_hour < 16:
        return {
            "session": "London",
            "volatility": "High",
            "trading_style": "Breakout Trading"
        }
    # New York session: 16:00 - 00:00 UTC
    else:
        return {
            "session": "New York",
            "volatility": "High",
            "trading_style": "Breakout Trading"
        }