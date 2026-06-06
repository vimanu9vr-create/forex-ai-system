"""
Killzones — ICT session windows, in UTC.

Three entry points:
  detect_killzone()      -> session for "now" (kept for existing callers; ranges fixed)
  in_killzone(ts)        -> session for a given candle timestamp (datetime or ISO str)
  is_entry_killzone(ts)  -> True only inside the high-volatility London / New York
                            killzones, where the intraday engine is allowed to take
                            liquidity-sweep entries.

Windows are UTC and tuned to winter (EST). London / NY shift ~1h in summer
(BST / EDT); set KILLZONE_OFFSET_HOURS to nudge every window without editing code.
Polygon and TwelveData both stamp forex candle datetimes in UTC, so no per-candle
timezone math is needed.

NOTE: the previous version's boundary checks (`current_minute < 0`) were dead code,
so e.g. London was effectively 07:00–08:59. This rewrite uses half-open hour ranges
[start, end) and a single source of truth (`_SESSIONS`).
"""

import os
from datetime import datetime

_OFFSET = int(os.getenv("KILLZONE_OFFSET_HOURS", "0"))

# name, start_hour (incl), end_hour (excl), volatility, trading_style, entry_allowed
_SESSIONS = [
    ("London Open",   7, 10, "High", "Liquidity Sweep / Reversal", True),
    ("New York Open", 12, 15, "High", "Liquidity Sweep / Reversal", True),
    ("Asian Session", 0,  5,  "Low",  "Range / Accumulation",       False),
]

_NONE = {"killzone": "None", "volatility": "Low", "trading_style": "Range", "entry_allowed": False}


def _to_datetime(ts):
    """Coerce a datetime or ISO-ish string ('YYYY-MM-DD HH:MM:SS' / date-only) to datetime."""
    if isinstance(ts, datetime):
        return ts
    if not ts:
        return None
    s = str(ts).strip().replace("Z", "").replace("T", " ")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        try:
            return datetime.fromisoformat(s[:10])  # date-only fallback
        except ValueError:
            return None


def _session_for_hour(hour):
    h = (hour - _OFFSET) % 24
    for name, start, end, vol, style, entry in _SESSIONS:
        if start <= h < end:
            return {"killzone": name, "volatility": vol, "trading_style": style, "entry_allowed": entry}
    return dict(_NONE)


def in_killzone(ts=None):
    """Session info for a given timestamp (datetime or ISO string); 'now' if None."""
    d = _to_datetime(ts) or datetime.utcnow()
    return _session_for_hour(d.hour)


def is_entry_killzone(ts=None):
    """True only inside the high-volatility London / NY killzones (intraday entries allowed)."""
    return bool(in_killzone(ts).get("entry_allowed", False))


def detect_killzone():
    """Session for 'now' (UTC). Kept for existing callers (live_pair_scanner et al.)."""
    return _session_for_hour(datetime.utcnow().hour)
