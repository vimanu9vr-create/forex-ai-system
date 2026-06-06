import os
from datetime import datetime

import requests


OANDA_API_KEY = os.getenv("OANDA_API_KEY")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")
OANDA_ENVIRONMENT = os.getenv("OANDA_ENVIRONMENT", "practice")
OANDA_LIVE_TRADING = os.getenv("OANDA_LIVE_TRADING", "false").lower() == "true"

BASE_URLS = {
    "practice": "https://api-fxpractice.oanda.com",
    "live": "https://api-fxtrade.oanda.com",
}


def is_configured():
    return bool(OANDA_API_KEY and OANDA_ACCOUNT_ID)


def status():
    return {
        "configured": is_configured(),
        "environment": OANDA_ENVIRONMENT,
        "live_trading_enabled": OANDA_LIVE_TRADING,
        "mode": "live" if is_configured() and OANDA_LIVE_TRADING else "paper",
    }


def format_instrument(pair):
    value = str(pair or "").replace("/", "").replace("_", "").upper()

    if len(value) == 6:
        return f"{value[:3]}_{value[3:]}"

    if value == "XAUUSD":
        return "XAU_USD"

    return value


def build_order_payload(signal, units):
    side = str(signal.get("signal", "BUY")).upper()
    signed_units = abs(int(units))

    if side == "SELL":
        signed_units *= -1

    return {
        "order": {
            "type": "MARKET",
            "instrument": format_instrument(signal.get("pair")),
            "units": str(signed_units),
            "timeInForce": "FOK",
            "positionFill": "DEFAULT",
        }
    }


def place_market_order(signal, units=1000):
    payload = build_order_payload(signal, units)

    if not is_configured() or not OANDA_LIVE_TRADING:
        return {
            "executed": False,
            "paper": True,
            "message": "OANDA credentials or live trading flag not enabled. Paper order prepared.",
            "order": payload,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

    base_url = BASE_URLS.get(OANDA_ENVIRONMENT, BASE_URLS["practice"])
    response = requests.post(
        f"{base_url}/v3/accounts/{OANDA_ACCOUNT_ID}/orders",
        headers={
            "Authorization": f"Bearer {OANDA_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=15,
    )
    response.raise_for_status()

    return {
        "executed": True,
        "paper": False,
        "order": payload,
        "response": response.json(),
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
