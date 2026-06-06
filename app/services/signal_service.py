import time
from datetime import datetime

from app.smart_money.live_pair_scanner import live_pair_scanner
from app.smart_money.risk_management import trade_levels

# ── Signal-level cache ─────────────────────────────────────────────────────
# Caches the fully-built signal list so the scanner only runs once per TTL
# regardless of how many WebSocket clients / HTTP polling hits arrive.
_signal_cache: dict = {"data": [], "ts": 0.0}
SIGNAL_CACHE_TTL = 300  # 5 minutes — matches TwelveData candle interval


def _signals_fresh() -> bool:
    return (time.time() - _signal_cache["ts"]) < SIGNAL_CACHE_TTL


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


def build_signal_from_scan(scan_result):
    """
    Build a dashboard signal from a scan result, or return None when there is
    no disciplined trade — i.e. no HTF-aligned direction, or price is not
    well-located for a >=1.5R structural entry. Returning None means the pair
    simply isn't shown, instead of surfacing a losing signal.
    """
    pair = scan_result.get("pair", "EURUSD")
    side = normalize_side(scan_result.get("direction"))
    candles = scan_result.get("candles") or []

    if side not in {"BUY", "SELL"} or not candles:
        return None  # no HTF-aligned directional bias

    try:
        levels = trade_levels(pair=pair, direction=side, candles=candles)
    except Exception:
        return None

    if not levels.get("valid"):
        return None  # price not well-located for a disciplined entry

    score = scan_result.get("confluence_score", scan_result.get("probability_score", 0))
    return {
        "pair": pair,
        "signal": side,
        "entry": levels.get("entry_price", 0),
        "stop_loss": levels.get("stop_loss", 0),
        "take_profit": levels.get("take_profit", 0),
        "confluence_score": normalize_probability(score),
        "timeframe": scan_result.get("timeframe", "1h"),
        "model": "Smart Money AI",
        "session": scan_result.get("session", "N/A"),
        "risk_reward": levels.get("risk_reward", "N/A"),
        "setup": levels.get("reason", ""),
        "htf_aligned": scan_result.get("htf_aligned", False),
        "bias": scan_result.get("signal_data", {}).get("bias", scan_result.get("bias")),
        "killzone": scan_result.get("signal_data", {}).get("killzone_active"),
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }


def get_live_signals(force: bool = False) -> list:
    """
    Return cached signals if fresh, otherwise run the scanner.
    All WebSocket pushes and HTTP /signals hits share the same cache,
    so TwelveData is called at most once per SIGNAL_CACHE_TTL seconds.
    """
    global _signal_cache

    if not force and _signals_fresh():
        return _signal_cache["data"]

    print(f"[signal_service] Cache miss — running live_pair_scanner at {datetime.utcnow().isoformat()}")

    try:
        scanner_payload = live_pair_scanner()
    except Exception as e:
        print(f"[signal_service] Scanner error: {e}")
        return _signal_cache["data"]  # serve stale on error

    scanned_pairs = scanner_payload.get("all_scanned_pairs", [])
    if not scanned_pairs and scanner_payload.get("best_pair"):
        scanned_pairs = [scanner_payload["best_pair"]]

    signals = []
    for r in scanned_pairs:
        if not isinstance(r, dict):
            continue
        sig = build_signal_from_scan(r)
        if sig:               # None = no disciplined setup for this pair
            signals.append(sig)
    signals.sort(key=lambda s: s["confluence_score"], reverse=True)

    _signal_cache = {"data": signals, "ts": time.time()}
    print(f"[signal_service] Cached {len(signals)} signals (TTL {SIGNAL_CACHE_TTL}s)")
    return signals


def signal_cache_status() -> dict:
    age = round(time.time() - _signal_cache["ts"])
    return {
        "cached_signals": len(_signal_cache["data"]),
        "age_seconds": age,
        "expires_in_seconds": max(0, SIGNAL_CACHE_TTL - age),
        "ttl_seconds": SIGNAL_CACHE_TTL,
    }
