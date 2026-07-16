import threading
import time
from datetime import datetime

from app.smart_money.live_pair_scanner import live_pair_scanner
from app.smart_money.risk_management import trade_levels

# ── Signal-level cache ─────────────────────────────────────────────────────
# Caches the fully-built signal list so the scanner only runs once per TTL
# regardless of how many WebSocket clients / HTTP polling hits arrive.
_signal_cache: dict = {}   # cache key ("all"/"disc" + pairs) -> {"data": [...], "ts": float}
SIGNAL_CACHE_TTL = 900  # 15 min — the multi-TF scan takes ~6min on the free tier, so a short
                        # TTL meant near-continuous re-scanning; daily/HTF data changes slowly.

# Stale-while-revalidate: a multi-TF dashboard scan can take minutes on the throttled Polygon
# tier, so a synchronous /signals call would time out the frontend ("network error"). Non-force
# calls return cached/empty INSTANTLY and refresh in a background thread (single-flight per key).
_refreshing: set = set()
_refresh_lock = threading.Lock()


def normalize_side(direction):
    value = str(direction or "").strip().upper()
    if value in {"BUY", "LONG"}:
        return "BUY"
    if value in {"SELL", "SHORT"}:
        return "SELL"
    return "HOLD"


def normalize_probability(value):
    try:
        probability = float(value)
    except (TypeError, ValueError):
        return 0
    if probability <= 1:
        probability *= 100
    return int(max(0, min(probability, 100)))


def build_signal_from_scan(scan_result, show_all=False):
    """
    Build a dashboard signal from a scan result.

    Disciplined mode (show_all=False, used by the SignalScheduler/alerts): returns None when
    there's no HTF-aligned direction or price isn't well-located for a >=1.5R entry — the pair
    is hidden rather than surfacing a losing signal.

    Dashboard mode (show_all=True): ALWAYS returns a row so every scanned pair is visible — a
    full setup (entry/SL/TP) when disciplined, otherwise a 'watch' row with the current
    direction/bias + confluence score and no executable levels.
    """
    pair = scan_result.get("pair", "EURUSD")
    side = normalize_side(scan_result.get("direction"))
    candles = scan_result.get("candles") or []
    score = normalize_probability(scan_result.get("confluence_score", scan_result.get("probability_score", 0)))

    levels = {}
    if side in {"BUY", "SELL"} and candles:
        try:
            levels = trade_levels(pair=pair, direction=side, candles=candles)
        except Exception:
            levels = {}
    disciplined = bool(side in {"BUY", "SELL"} and levels.get("valid"))

    if not disciplined and not show_all:
        return None  # keep alerts/validated path clean

    # Show the computed entry/SL/TP whether it's an A+ setup (disciplined) or an INDICATIVE
    # watch trade. trade_levels now returns levels even when valid=False (directional pairs);
    # HOLD/neutral pairs get 0s (rendered as "—" in the UI).
    entry = levels.get("entry_price", 0)
    sl = levels.get("stop_loss", 0)
    tp = levels.get("take_profit", 0)
    rr = levels.get("risk_reward", "N/A")
    setup = levels.get("reason") or (
        f"{side} bias — watching" if side in ("BUY", "SELL") else "Ranging / no clear HTF trend — watching")

    return {
        "pair": pair,
        "signal": side,                # BUY / SELL / HOLD
        "entry": entry,
        "stop_loss": sl,
        "take_profit": tp,
        "confluence_score": score,
        "timeframe": scan_result.get("timeframe", "1h"),
        "model": "Smart Money AI",
        "session": scan_result.get("session", "N/A"),
        "risk_reward": rr,
        "setup": setup,
        "status": "setup" if disciplined else "watch",
        "htf_aligned": scan_result.get("htf_aligned", False),
        "bias": scan_result.get("signal_data", {}).get("bias", scan_result.get("bias")),
        "killzone": scan_result.get("signal_data", {}).get("killzone_active"),
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }


def get_live_signals(force: bool = False, pairs=None, timeframes=None, show_all: bool = False) -> list:
    """
    Return cached signals if fresh, otherwise run the scanner.

    pairs      — which pairs to scan (default STRATEGY_PAIRS, resolved in the scanner).
    timeframes — which timeframes (15min, 1h, 4h, 1day, etc.). Default STRATEGY_TIMEFRAME.
    show_all   — dashboard mode: surface a row for EVERY scanned pair (high-probability setups
                 sort to the top; low-conviction pairs show as 'watch' rows). Disciplined mode
                 (default) hides non-setups — used by the SignalScheduler/alerts.

    Cached per (mode, pairs) so the dashboard's all-pairs view and the scheduler's validated
    2-pair view don't clobber each other's cache.
    """
    key = f"{'all' if show_all else 'disc'}:{','.join(pairs or [])}:{','.join(timeframes or [])}"
    slot = _signal_cache.get(key)
    fresh = slot and (time.time() - slot["ts"]) < SIGNAL_CACHE_TTL

    if fresh and not force:
        return slot["data"]
    if force:
        return _scan_and_cache(key, pairs, timeframes, show_all)   # synchronous (scheduler / pre-warm)

    # Stale-while-revalidate: refresh in the background, return stale/empty NOW so the caller
    # (dashboard) never blocks on a multi-minute throttled scan.
    _kick_background_refresh(key, pairs, timeframes, show_all)
    return slot["data"] if slot else []


def _payload_to_signals(scanner_payload, show_all: bool) -> list:
    scanned = scanner_payload.get("all_scanned_pairs", [])
    if not scanned and scanner_payload.get("best_pair"):
        scanned = [scanner_payload["best_pair"]]
    out = []
    for r in scanned:
        if isinstance(r, dict):
            sig = build_signal_from_scan(r, show_all=show_all)
            if sig:               # None only in disciplined mode (no A+ setup)
                out.append(sig)
    return out


def _scan_and_cache(key: str, pairs, timeframes, show_all: bool) -> list:
    """Run the scanner, build + cache signals for `key`. Serves stale on error.

    Multi-pair (dashboard) scans run PER PAIR and update the cache after each one, so rows
    appear PROGRESSIVELY (first pair in ~1min) instead of empty-for-6min-then-all-28-at-once.
    """
    print(f"[signal_service] Scanning ({key}) at {datetime.utcnow().isoformat()}")

    if pairs and len(pairs) > 1:
        signals = []
        for p in pairs:
            try:
                payload = live_pair_scanner(pairs=[p], timeframes=timeframes)
            except Exception as e:
                print(f"[signal_service] scan {p} error: {e}")
                continue
            signals.extend(_payload_to_signals(payload, show_all))
            signals.sort(key=lambda s: s["confluence_score"], reverse=True)
            _signal_cache[key] = {"data": list(signals), "ts": time.time()}   # publish after each pair
        print(f"[signal_service] Cached {len(signals)} signals for {key} (incremental, {len(pairs)} pairs)")
        return signals

    # Single/small scan (scheduler default path)
    try:
        payload = live_pair_scanner(pairs=pairs, timeframes=timeframes)
    except Exception as e:
        print(f"[signal_service] Scanner error: {e}")
        return _signal_cache.get(key, {}).get("data", [])   # serve stale on error
    signals = sorted(_payload_to_signals(payload, show_all), key=lambda s: s["confluence_score"], reverse=True)
    _signal_cache[key] = {"data": signals, "ts": time.time()}
    print(f"[signal_service] Cached {len(signals)} signals for {key}")
    return signals


def _kick_background_refresh(key: str, pairs, timeframes, show_all: bool):
    """Start a single-flight background scan for `key` (no-op if one is already running)."""
    with _refresh_lock:
        if key in _refreshing:
            return
        _refreshing.add(key)

    def _run():
        try:
            _scan_and_cache(key, pairs, timeframes, show_all)
        finally:
            with _refresh_lock:
                _refreshing.discard(key)

    threading.Thread(target=_run, daemon=True, name="signal-refresh").start()


def signal_cache_status() -> dict:
    out = {"ttl_seconds": SIGNAL_CACHE_TTL, "modes": {}}
    for key, slot in _signal_cache.items():
        age = round(time.time() - slot["ts"])
        out["modes"][key] = {
            "cached_signals": len(slot["data"]),
            "age_seconds": age,
            "expires_in_seconds": max(0, SIGNAL_CACHE_TTL - age),
        }
    return out
