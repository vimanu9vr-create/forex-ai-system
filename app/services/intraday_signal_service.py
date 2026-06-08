"""
intraday_signal_service — top-down feed for the dedicated liquidity-sweep engine.

Per pair, faithfully top-down:
  1. Daily + 4H  -> HTF bias (htf_bias_from). Neutral => stand aside (no setup).
  2. Daily       -> draw-on-liquidity targets (prev day/week high-low).
  3. entry TF    -> analyze_intraday, hard-filtered to the HTF direction, TP at the draw.

`tf` selects the entry timeframe ("5min" or "15min"). Cached per-tf so many
WebSocket/HTTP hits share one scan. SEPARATE from the daily-edge signal_service.
"""

import threading
import time
from datetime import datetime

from app.config import INTRADAY_PAIRS, INTRADAY_TIMEFRAME, INTRADAY_MIN_RR
from app.services.market_data import get_forex_intraday
from app.smart_money.intraday_engine import analyze_intraday, htf_bias_from

_cache: dict = {}          # "tf:session" -> {"data": [...], "ts": float}
TTL = 180                  # 3 min
VALID_TFS = {"5min", "15min"}

# Session views — let the dashboard analyze London and New York separately. London is the
# validated default (NY bled in the backtest); NY/both are analysis-only.
SESSIONS = {
    "london":  {"London Open"},
    "newyork": {"New York Open"},
    "ny":      {"New York Open"},
    "both":    {"London Open", "New York Open"},
    "all":     {"London Open", "New York Open"},
}
DEFAULT_SESSION = "london"


def _pip(pair: str) -> float:
    return 0.01 if "JPY" in pair.upper() else 0.0001


def _grade(sig: dict) -> str:
    """A+/A/B quality label (all signals are HTF-aligned + London-killzone + wider-stop by
    construction). Recalibrated to the 1.5R floor after the desk corrections — the old 2/3R
    thresholds would have graded almost everything 'B' once targets moved nearer."""
    try:
        rr = float(sig.get("risk_reward") or 0)
    except (TypeError, ValueError):
        rr = 0.0
    fvg = sig.get("entry_basis") == "FVG"
    if fvg and rr >= 2.5:
        return "A+"
    if (fvg and rr >= 1.8) or rr >= 2.5:
        return "A"
    return "B"


def _candle_age_min(candles: list):
    try:
        last = str(candles[-1]["datetime"]).replace("Z", "").replace("T", " ")
        return (datetime.utcnow() - datetime.fromisoformat(last)).total_seconds() / 60.0
    except Exception:
        return None


def _is_valid(sig: dict) -> bool:
    """Final guard — never surface a malformed signal."""
    try:
        e, sl, tp = float(sig["entry"]), float(sig["stop_loss"]), float(sig["take_profit"])
        rr = float(sig.get("risk_reward") or 0)
    except (TypeError, ValueError, KeyError):
        return False
    ordered = (sl < e < tp) if sig["signal"] == "BUY" else (tp < e < sl)
    return ordered and rr >= INTRADAY_MIN_RR


def _enrich(sig: dict, pair: str, tf: str, candles: list) -> dict:
    """Add grade, risk in pips, TP ladder, freshness, and a management plan."""
    pip = _pip(pair)
    risk_pips = round(abs(sig["entry"] - sig["stop_loss"]) / pip, 1)
    reward_pips = round(abs(sig["take_profit"] - sig["entry"]) / pip, 1)
    age = _candle_age_min(candles)
    tf_min = 5 if tf == "5min" else 15
    sig["grade"] = _grade(sig)
    sig["risk_pips"] = risk_pips
    sig["reward_pips"] = reward_pips
    sig["tp1"] = sig["take_profit"]              # nearest opposing liquidity — first partial
    sig["tp2"] = sig.get("runner_target")        # HTF draw — runner
    sig["candle_age_min"] = round(age) if age is not None else None
    sig["fresh"] = bool(age is not None and age <= tf_min * 3)
    sig["management"] = (
        f"Risk {risk_pips} pips = 1% of account. TP1 {sig['take_profit']} "
        f"(+{reward_pips} pips, {sig.get('risk_reward')}R): close ~50%, move SL to break-even. "
        f"Runner to {sig.get('runner_target')} (HTF draw); trail behind {tf} structure."
    )
    return sig


def _draw_targets(daily: list):
    """HTF draw-on-liquidity: previous day & previous-week highs/lows."""
    if not daily or len(daily) < 7:
        return [], {}
    pdh, pdl = daily[-2]["high"], daily[-2]["low"]
    week = daily[-6:-1]
    pwh, pwl = max(c["high"] for c in week), min(c["low"] for c in week)
    meta = {"prev_day_high": pdh, "prev_day_low": pdl,
            "prev_week_high": pwh, "prev_week_low": pwl}
    return [pdh, pdl, pwh, pwl], meta


def _scan_pair(pair: str, tf: str, allowed_kz) -> dict:
    """Top-down scan of ONE pair -> a validated, enriched signal dict, or None.
    Self-contained per pair so the scan can run pairs concurrently (network-bound)."""
    try:
        daily = get_forex_intraday(pair, interval="1day", outputsize=200)
        h4 = get_forex_intraday(pair, interval="4h", outputsize=200)
        bias, d_dir, h_dir = htf_bias_from(daily, h4)
        if bias == "neutral":
            return None  # no clear HTF draw -> stand aside (the methodology)
        draws, draw_meta = _draw_targets(daily)
        candles = get_forex_intraday(pair, interval=tf, outputsize=500)
        sig = analyze_intraday(pair, candles or [], htf_bias=bias, tf=tf,
                               draw_targets=draws, allowed_killzones=allowed_kz)
    except Exception as e:
        print(f"[intraday_signal_service] {pair} {tf} error: {e}")
        return None
    if not sig:
        return None
    sig["htf_daily"] = d_dir
    sig["htf_4h"] = h_dir
    sig["draw_levels"] = draw_meta
    # Runner target = the far HTF draw in the trade direction (TP is the nearest pool;
    # the runner is where the rest can ride to).
    sig["runner_target"] = (draw_meta.get("prev_week_high") if sig["signal"] == "BUY"
                            else draw_meta.get("prev_week_low"))
    sig = _enrich(sig, pair, tf, candles)
    return sig if _is_valid(sig) else None           # final guard — drop anything malformed


_refresh_lock = threading.Lock()
_refresh_active = False             # at most ONE intraday bg scan at a time


def _scan_all(tf: str, allowed_kz, key: str) -> list:
    """Full sequential scan of INTRADAY_PAIRS -> sorted, cached signal list.
    Sequential on purpose: Polygon shares one API key across the app + schedulers, so a
    concurrent burst trips the per-minute rate limit (429 -> 20s retry, far slower). Daily/4H
    are long-TTL cached in market_data (2h/1h), so after warm-up a scan is mostly the 15m fetch."""
    signals = [s for s in (_scan_pair(p, tf, allowed_kz) for p in INTRADAY_PAIRS) if s]
    _grade_rank = {"A+": 3, "A": 2, "B": 1}   # best grade first, then strongest confluence
    signals.sort(key=lambda s: (_grade_rank.get(s.get("grade"), 0), s["quality_score"]), reverse=True)
    _cache[key] = {"data": signals, "ts": time.time()}
    print(f"[intraday_signal_service] {key}: {len(signals)} signal(s) across {len(INTRADAY_PAIRS)} pairs "
          f"at {datetime.utcnow().isoformat()}")
    return signals


def _kick_background_refresh(tf: str, allowed_kz, key: str):
    """Run a scan in a daemon thread so requests never block on the ~2min cold network scan.
    Single-flight across ALL keys: london/newyork/both share the same rate-limited Polygon
    raw data, so running them at once just trips the rate limit. One scan at a time warms the
    shared raw data; the next 60s poll kicks whatever key is still stale (then resolves fast)."""
    global _refresh_active
    with _refresh_lock:
        if _refresh_active:
            return
        _refresh_active = True

    def _run():
        global _refresh_active
        try:
            _scan_all(tf, allowed_kz, key)
        except Exception as e:
            print(f"[intraday_signal_service] bg refresh {key} error: {e}")
        finally:
            with _refresh_lock:
                _refresh_active = False

    threading.Thread(target=_run, daemon=True, name=f"intraday-warm-{key}").start()


def get_intraday_signals(force: bool = False, tf: str = INTRADAY_TIMEFRAME,
                         session: str = DEFAULT_SESSION) -> list:
    """Top-down setups for the chosen entry TF + session (cached, stale-while-revalidate).
    session = 'london' (validated default) | 'newyork' | 'both' — restricts which killzone's
    sweeps qualify, so the dashboard can analyze London and NY separately.

    The dashboard path (force=False) NEVER blocks on the cold scan: it returns the cached
    result immediately (fresh, or stale while a background refresh runs, or [] on first-ever
    load) and the 60s poll picks up the fresh data moments later. force=True (the alert
    scheduler / pre-warm) does a synchronous fresh scan."""
    tf = tf if tf in VALID_TFS else INTRADAY_TIMEFRAME
    session = session.lower() if isinstance(session, str) else DEFAULT_SESSION
    allowed_kz = SESSIONS.get(session, SESSIONS[DEFAULT_SESSION])
    key = f"{tf}:{session}"
    slot = _cache.get(key)

    if force:
        return _scan_all(tf, allowed_kz, key)          # synchronous fresh scan
    if slot and (time.time() - slot["ts"]) < TTL:
        return slot["data"]                            # fresh cache hit
    _kick_background_refresh(tf, allowed_kz, key)       # stale or cold -> refresh off-thread
    return slot["data"] if slot else []                # serve stale now, or [] while warming


def intraday_cache_status() -> dict:
    out = {"ttl_seconds": TTL, "timeframes": {}}
    for tf, slot in _cache.items():
        age = round(time.time() - slot["ts"])
        out["timeframes"][tf] = {
            "cached_signals": len(slot["data"]),
            "age_seconds": age,
            "expires_in_seconds": max(0, TTL - age),
        }
    return out
