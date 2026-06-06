import time
import threading
import requests
from app.config import TWELVEDATA_API_KEY

BASE_URL = "https://api.twelvedata.com/time_series"

# ── In-memory cache ────────────────────────────────────────────────────────
_cache: dict = {}

# ── Rate limiter — free tier allows ~8 credits/min; stay under it so multi-pair
#    scans don't get starved with "out of API credits" empty responses. ───────
_RATE_LOCK = threading.Lock()
_call_times: list = []
_MAX_CALLS_PER_WINDOW = 7
_RATE_WINDOW = 60.0


def _throttle():
    """Block just long enough to keep TwelveData calls under the per-minute cap."""
    with _RATE_LOCK:
        now = time.time()
        while _call_times and now - _call_times[0] > _RATE_WINDOW:
            _call_times.pop(0)
        if len(_call_times) >= _MAX_CALLS_PER_WINDOW:
            wait = _RATE_WINDOW - (now - _call_times[0]) + 0.05
            if wait > 0:
                time.sleep(wait)
            now = time.time()
            while _call_times and now - _call_times[0] > _RATE_WINDOW:
                _call_times.pop(0)
        _call_times.append(time.time())

# Cache TTLs per timeframe — longer TF data changes slower
_TTL_MAP = {
    "5min":  300,
    "15min": 600,
    "30min": 900,
    "1h":    1800,
    "4h":    3600,
    "1day":  7200,
}
DEFAULT_TTL = 900


def _cache_key(pair: str, interval: str) -> str:
    return f"{pair.upper()}_{interval}"


def _ttl(interval: str) -> int:
    return _TTL_MAP.get(interval, DEFAULT_TTL)


def _is_fresh(key: str, interval: str) -> bool:
    entry = _cache.get(key)
    if not entry:
        return False
    return (time.time() - entry["ts"]) < _ttl(interval)


def get_forex_intraday(pair: str = "EURUSD", interval: str = "1h", outputsize: int = 200) -> list:
    """
    Fetch OHLC candles for a forex pair.
    Defaults: 1h / 200 candles — enough for proper SMC swing analysis.

    Recommended per pair for full SMC:
      H4 (interval="4h",  outputsize=100) — HTF bias + major structure
      H1 (interval="1h",  outputsize=200) — OB / FVG / intermediate structure
      M15(interval="15min",outputsize=100) — Entry precision / confirmation
    """
    key = _cache_key(pair, interval)

    if _is_fresh(key, interval):
        return _cache[key]["data"]

    # Prefer Polygon (real tick-volume + high rate limits) when configured;
    # fall back to TwelveData (OHLC only, throttled) otherwise.
    try:
        from app.services.polygon_service import get_polygon_candles, is_configured as _polygon_ok
        if _polygon_ok():
            pcandles = get_polygon_candles(pair, interval, outputsize)
            if pcandles:
                _cache[key] = {"data": pcandles, "ts": time.time()}
                print(f"[market_data] {pair} {interval}: {len(pcandles)} candles via Polygon (with volume)")
                return pcandles
    except Exception as e:
        print(f"[market_data] Polygon path error for {pair} {interval}: {e}; using TwelveData")

    try:
        symbol = f"{pair[:3]}/{pair[3:]}"
        params = {
            "symbol":     symbol,
            "interval":   interval,
            "outputsize": outputsize,
            "apikey":     TWELVEDATA_API_KEY,
            "format":     "JSON",
        }

        _throttle()
        response = requests.get(BASE_URL, params=params, timeout=15)
        data = response.json()

        if "values" not in data:
            if key in _cache:
                print(f"[market_data] API error {pair} {interval}, stale cache returned. "
                      f"Msg: {data.get('message','')}")
                return _cache[key]["data"]
            print(f"[market_data] No data {pair} {interval}: {data.get('message', data)}")
            return []

        # TwelveData returns newest-first → reverse to oldest-first
        candles = [
            {
                "datetime": item["datetime"],
                "open":  float(item["open"]),
                "high":  float(item["high"]),
                "low":   float(item["low"]),
                "close": float(item["close"]),
            }
            for item in reversed(data["values"])
        ]

        _cache[key] = {"data": candles, "ts": time.time()}
        print(f"[market_data] {pair} {interval}: {len(candles)} candles cached")
        return candles

    except Exception as e:
        print(f"[market_data] Error {pair} {interval}: {e}")
        if key in _cache:
            return _cache[key]["data"]
        return []


def get_multi_timeframe(pair: str) -> dict:
    """
    Fetch H4 + H1 + M15 in one call.
    Returns {"h4": [...], "h1": [...], "m15": [...]}
    """
    return {
        "h4":  get_forex_intraday(pair, interval="4h",    outputsize=100),
        "h1":  get_forex_intraday(pair, interval="1h",    outputsize=200),
        "m15": get_forex_intraday(pair, interval="15min", outputsize=100),
    }


def clear_cache(pair: str = None):
    if pair:
        for interval in list(_TTL_MAP.keys()):
            _cache.pop(_cache_key(pair, interval), None)
    else:
        _cache.clear()
    print(f"[market_data] Cache cleared: {pair or 'ALL'}")


def cache_status() -> dict:
    now = time.time()
    return {
        key: {
            "age_seconds": round(now - entry["ts"]),
            "expires_in":  max(0, round(_ttl(key.split("_", 1)[-1]) - (now - entry["ts"]))),
            "candles":     len(entry["data"]),
        }
        for key, entry in _cache.items()
    }
