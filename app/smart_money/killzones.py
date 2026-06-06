from datetime import datetime

def detect_killzone():
    now = datetime.utcnow()
    current_hour = now.hour
    current_minute = now.minute

    # London Open Killzone: 07:00 - 09:00 UTC
    if (current_hour == 7 and current_minute >= 0) or (current_hour == 8) or (current_hour == 9 and current_minute < 0):
        return {
            "killzone": "London Open",
            "volatility": "High",
            "trading_style": "Breakout Trading"
        }
    # New York Open Killzone: 12:00 - 14:00 UTC
    elif (current_hour == 12 and current_minute >= 0) or (current_hour == 13) or (current_hour == 14 and current_minute < 0):
        return {
            "killzone": "New York Open",
            "volatility": "High",
            "trading_style": "Breakout Trading"
        }
    # Asian Session Killzone: 23:00 - 01:00 UTC
    elif (current_hour == 23 and current_minute >= 0) or (current_hour == 0) or (current_hour == 1 and current_minute < 0):
        return {
            "killzone": "Asian Session",
            "volatility": "Low",
            "trading_style": "Range Trading"
        }
    else:
        return {
            "killzone": "None",
            "volatility": "Low",
            "trading_style": "Range Trading"
        }