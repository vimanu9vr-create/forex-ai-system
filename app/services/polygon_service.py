"""
Polygon.io forex candle feed — includes real tick-volume (`v`) and transaction
count (`n`), which TwelveData does not provide for forex. Used as the primary
candle source (high rate limits + volume); market_data falls back to TwelveData
when Polygon is not configured or returns nothing.

Forex tickers use the C: prefix, e.g. EURUSD -> C:EURUSD.
"""

import math
import time
import datetime as dt

import requests

from app.config import POLYGON_API_KEY

BASE = "https://api.polygon.io"

# interval -> (multiplier, timespan, minutes_per_candle)
_TF = {
    "5min":  (5,  "minute", 5),
    "15min": (15, "minute", 15),
    "30min": (30, "minute", 30),
    "1h":    (1,  "hour",   60),
    "4h":    (4,  "hour",   240),
    "1day":  (1,  "day",    1440),
}


def is_configured() -> bool:
    return bool(POLYGON_API_KEY)


def _lookback_days(minutes: int, outputsize: int) -> int:
    # trading minutes -> calendar days, padded for weekends (forex ~5/7) + buffer
    return max(3, math.ceil(outputsize * minutes / 1440 * 1.5) + 3)


def _ticker(pair: str) -> str:
    clean = str(pair or "").replace("/", "").replace("_", "").upper()
    return f"C:{clean}"


def get_polygon_candles(pair: str, interval: str = "1h", outputsize: int = 200, retries: int = 4) -> list:
    """Return up to `outputsize` oldest-first OHLCV candles, or [] on failure.
    Retries with a pause on the per-minute rate limit so deep history downloads."""
    if not POLYGON_API_KEY:
        return []

    mult, span, minutes = _TF.get(interval, _TF["1h"])
    to = dt.date.today()
    frm = to - dt.timedelta(days=_lookback_days(minutes, outputsize))
    url = f"{BASE}/v2/aggs/ticker/{_ticker(pair)}/range/{mult}/{span}/{frm}/{to}"

    for attempt in range(retries + 1):
        try:
            r = requests.get(
                url,
                params={"apiKey": POLYGON_API_KEY, "sort": "asc", "limit": 50000},
                timeout=30,
            )
            data = r.json() if r.content else {}
            msg = str((data or {}).get("error") or (data or {}).get("message") or "")

            # Rate limited → wait and retry
            if r.status_code == 429 or "exceeded" in msg.lower() or "maximum requests" in msg.lower():
                if attempt < retries:
                    time.sleep(20)
                    continue
                print(f"[polygon] {pair} {interval}: rate-limited, giving up")
                return []

            results = data.get("results") or []
            if not results:
                if (data or {}).get("status") not in ("OK", "DELAYED"):
                    print(f"[polygon] {pair} {interval}: {msg[:140]}")
                return []

            return [
                {
                    "datetime": dt.datetime.utcfromtimestamp(x["t"] / 1000).strftime("%Y-%m-%d %H:%M:%S"),
                    "open":  float(x["o"]),
                    "high":  float(x["h"]),
                    "low":   float(x["l"]),
                    "close": float(x["c"]),
                    "volume": float(x.get("v", 0) or 0),
                }
                for x in results
                if all(k in x for k in ("o", "h", "l", "c", "t"))
            ][-outputsize:]

        except Exception as e:
            if attempt < retries:
                time.sleep(5)
                continue
            print(f"[polygon] error {pair} {interval}: {e}")
            return []
    return []
