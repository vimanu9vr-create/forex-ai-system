"""
Macro feed (Finnhub) — economic calendar + market news, used to gate / caution
trades around high-impact events and provide macro context to the desk analysis.

Free-tier notes: `/calendar/economic` and `/news` are available; `/forex/rates`
is premium. Calendar + news are global, so they're fetched once and cached;
`macro_context(pair)` just filters the cache to the pair's two currencies, so a
full 7-pair scan costs at most ~2 Finnhub calls per TTL.
"""

import time
import datetime as dt

import requests

from app.config import FINNHUB_API_KEY

BASE = "https://finnhub.io/api/v1"
_TTL = 1800  # 30 min
_cache: dict = {}

_COUNTRY_CCY = {
    "US": "USD", "EU": "EUR", "DE": "EUR", "FR": "EUR", "IT": "EUR", "ES": "EUR",
    "GB": "GBP", "UK": "GBP", "JP": "JPY", "CA": "CAD", "CH": "CHF",
    "AU": "AUD", "NZ": "NZD", "CN": "CNY",
}


def is_configured() -> bool:
    return bool(FINNHUB_API_KEY)


def _cached(key: str, fn):
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[0] < _TTL:
        return hit[1]
    data = fn()
    _cache[key] = (now, data)
    return data


def _impact_level(val) -> str:
    s = str(val).strip().lower()
    if s in ("high", "3"):
        return "high"
    if s in ("medium", "2"):
        return "medium"
    return "low"


def _fetch_calendar() -> list:
    if not FINNHUB_API_KEY:
        return []
    today = dt.date.today()
    to = today + dt.timedelta(days=7)
    try:
        r = requests.get(f"{BASE}/calendar/economic",
                         params={"from": str(today), "to": str(to), "token": FINNHUB_API_KEY},
                         timeout=20)
        events = (r.json() or {}).get("economicCalendar") or []
        out = []
        for e in events:
            country = str(e.get("country", "")).upper()[:2]
            out.append({
                "currency": _COUNTRY_CCY.get(country, country),
                "event": e.get("event", ""),
                "impact": _impact_level(e.get("impact")),
                "time": e.get("time", ""),
                "actual": e.get("actual"),
                "estimate": e.get("estimate"),
                "prev": e.get("prev"),
            })
        return out
    except Exception as ex:
        print(f"[macro] calendar error: {ex}")
        return []


def _fetch_news() -> list:
    if not FINNHUB_API_KEY:
        return []
    try:
        r = requests.get(f"{BASE}/news", params={"category": "general", "token": FINNHUB_API_KEY}, timeout=20)
        items = r.json()
        if not isinstance(items, list):
            return []
        return [{"headline": i.get("headline", ""), "source": i.get("source", "")} for i in items[:10]]
    except Exception as ex:
        print(f"[macro] news error: {ex}")
        return []


def macro_context(pair: str) -> dict:
    """Macro picture for a pair's two currencies: high/medium-impact events,
    an event-risk flag, and a few market headlines."""
    if not FINNHUB_API_KEY:
        return {"available": False, "note": "Finnhub not configured"}

    ccys = {str(pair)[:3].upper(), str(pair)[3:].upper()}
    calendar = _cached("calendar", _fetch_calendar)
    news = _cached("news", _fetch_news)

    relevant = [e for e in calendar if e["currency"] in ccys and e["impact"] in ("high", "medium")]
    high = [e for e in relevant if e["impact"] == "high"]

    return {
        "available": True,
        "currencies": sorted(ccys),
        "high_impact_events": high[:5],
        "medium_impact_events": [e for e in relevant if e["impact"] == "medium"][:5],
        "event_risk": "elevated" if high else "normal",
        "headlines": [n["headline"] for n in news[:3]],
    }
