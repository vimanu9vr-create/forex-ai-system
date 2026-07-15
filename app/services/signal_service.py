import time
from datetime import datetime

from app.smart_money.live_pair_scanner import live_pair_scanner
from app.smart_money.risk_management import trade_levels

# ── Signal-level cache ─────────────────────────────────────────────────────
# Caches the fully-built signal list so the scanner only runs once per TTL
# regardless of how many WebSocket clients / HTTP polling hits arrive.
_signal_cache: dict = {}   # cache key ("all"/"disc" + pairs) -> {"data": [...], "ts": float}
SIGNAL_CACHE_TTL = 300  # 5 minutes — matches TwelveData candle interval


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
    if not force and slot and (time.time() - slot["ts"]) < SIGNAL_CACHE_TTL:
        return slot["data"]

    print(f"[signal_service] Cache miss ({key}) — running live_pair_scanner at {datetime.utcnow().isoformat()}")
    try:
        scanner_payload = live_pair_scanner(pairs=pairs, timeframes=timeframes)
    except Exception as e:
        print(f"[signal_service] Scanner error: {e}")
        return slot["data"] if slot else []   # serve stale on error

    scanned_pairs = scanner_payload.get("all_scanned_pairs", [])
    if not scanned_pairs and scanner_payload.get("best_pair"):
        scanned_pairs = [scanner_payload["best_pair"]]

    signals = []
    for r in scanned_pairs:
        if not isinstance(r, dict):
            continue
        sig = build_signal_from_scan(r, show_all=show_all)
        if sig:               # None only in disciplined mode (no A+ setup)
            signals.append(sig)
    signals.sort(key=lambda s: s["confluence_score"], reverse=True)

    _signal_cache[key] = {"data": signals, "ts": time.time()}
    print(f"[signal_service] Cached {len(signals)} signals for {key} (TTL {SIGNAL_CACHE_TTL}s)")
    return signals


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
