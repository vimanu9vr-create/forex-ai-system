"""
intraday_forward_test — a live paper-forward log for the intraday sweep engine.

The backtest sample is tiny (19 trades), so its +0.68R is directional, not proven. This
records EVERY signal the engine emits live (deduped), then evaluates each one against the
candles that printed AFTER it — limit fill within a few bars, then SL/TP (SL-priority,
conservative) — to accumulate a real out-of-sample track record by session and pair.

Storage: one JSON line per signal in INTRADAY_FORWARD_LOG (default under the Docker data
volume so it survives rebuilds). Outcomes are GROSS of spread/slippage (a forward demo, not
a fill simulator); treat them as optimistic. `log_signals` is called from each engine scan;
`forward_test_stats` lazily evaluates open records and returns the aggregate.
"""

import json
import os
import threading
from datetime import datetime

from app.services.market_data import get_forex_intraday

FILL_BARS = 8        # limit entry must fill within ~2h (15m) or the setup expires
_LOCK = threading.Lock()


def _log_path() -> str:
    env = os.getenv("INTRADAY_FORWARD_LOG")
    if env:
        return env
    return "/data/intraday_forward_test.jsonl" if os.path.isdir("/data") else "intraday_forward_test.jsonl"


def _key(sig: dict) -> str:
    return f"{sig.get('pair')}|{sig.get('signal')}|{sig.get('entry')}|{sig.get('sweep_time')}"


def _load() -> list:
    path = _log_path()
    if not os.path.exists(path):
        return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    return out


def _save(records: list):
    path = _log_path()
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    os.replace(tmp, path)


def log_signals(signals: list):
    """Append any NOT-yet-seen signals as open forward-test records. Safe to call every scan."""
    if not signals:
        return
    with _LOCK:
        records = _load()
        seen = {r["key"] for r in records}
        added = 0
        for s in signals:
            k = _key(s)
            if k in seen:
                continue
            seen.add(k)
            records.append({
                "key": k,
                "pair": s.get("pair"),
                "signal": s.get("signal"),
                "tf": s.get("timeframe", "15min"),
                "session": s.get("killzone"),
                "entry": s.get("entry"),
                "stop_loss": s.get("stop_loss"),
                "take_profit": s.get("take_profit"),
                "risk_reward": s.get("risk_reward"),
                "grade": s.get("grade"),
                "quality_score": s.get("quality_score"),
                "htf_bias": s.get("htf_bias"),
                "sweep_time": s.get("sweep_time"),
                "logged_at": datetime.utcnow().isoformat() + "Z",
                "status": "pending",      # pending -> open(filled) -> win/loss, or expired(no fill)
                "result": None, "R": None, "exit_at": None,
            })
            added += 1
        if added:
            _save(records)
            print(f"[intraday_forward_test] logged {added} new signal(s); {len(records)} total")


def _evaluate(rec: dict) -> bool:
    """Resolve one record against later candles. Returns True if it changed."""
    if rec["status"] in ("win", "loss", "expired"):
        return False
    candles = get_forex_intraday(rec["pair"], rec.get("tf", "15min"), 500) or []
    t0 = str(rec.get("sweep_time") or rec.get("logged_at"))
    after = [c for c in candles if str(c["datetime"]) > t0]
    if not after:
        return False
    entry, sl, tp, side = rec["entry"], rec["stop_loss"], rec["take_profit"], rec["signal"]

    fill_i = next((i for i, c in enumerate(after[:FILL_BARS])
                   if (side == "BUY" and c["low"] <= entry) or (side == "SELL" and c["high"] >= entry)), None)
    if fill_i is None:
        if len(after) >= FILL_BARS:           # waited long enough, never filled
            rec.update(status="expired", result="no_fill")
            return True
        return False

    for c in after[fill_i:]:
        if side == "BUY":
            hit_sl, hit_tp = c["low"] <= sl, c["high"] >= tp
        else:
            hit_sl, hit_tp = c["high"] >= sl, c["low"] <= tp
        if hit_sl:                            # SL priority (conservative)
            rec.update(status="loss", result="loss", R=-1.0, exit_at=c["datetime"])
            return True
        if hit_tp:
            rec.update(status="win", result="win", R=float(rec.get("risk_reward") or 0), exit_at=c["datetime"])
            return True
    if rec["status"] != "open":               # filled, still running
        rec.update(status="open", result="filled_open")
        return True
    return False


def _bucket():
    return {"trades": 0, "wins": 0, "losses": 0, "R": 0.0}


def forward_test_stats() -> dict:
    """Evaluate open records against fresh candles, then return the aggregate track record."""
    with _LOCK:
        records = _load()
        changed = False
        for r in records:
            try:
                changed = _evaluate(r) or changed
            except Exception as e:
                print(f"[intraday_forward_test] eval error {r.get('key')}: {e}")
        if changed:
            _save(records)

    closed = [r for r in records if r["status"] in ("win", "loss")]
    wins = [r for r in closed if r["status"] == "win"]
    total_R = sum(float(r.get("R") or 0) for r in closed)
    by_session, by_pair = {}, {}
    for r in closed:
        for grp, kk in ((by_session, r.get("session") or "?"), (by_pair, r.get("pair") or "?")):
            b = grp.setdefault(kk, _bucket())
            b["trades"] += 1
            b["wins"] += 1 if r["status"] == "win" else 0
            b["losses"] += 1 if r["status"] == "loss" else 0
            b["R"] = round(b["R"] + float(r.get("R") or 0), 2)
    for grp in (by_session, by_pair):
        for b in grp.values():
            b["win_rate_pct"] = round(b["wins"] / b["trades"] * 100, 1) if b["trades"] else 0

    return {
        "note": "Live demo-forward log. Outcomes are GROSS of spread/slippage — optimistic.",
        "logged_total": len(records),
        "pending": sum(1 for r in records if r["status"] == "pending"),
        "open": sum(1 for r in records if r["status"] == "open"),
        "expired_no_fill": sum(1 for r in records if r["status"] == "expired"),
        "closed": len(closed),
        "wins": len(wins),
        "losses": len(closed) - len(wins),
        "win_rate_pct": round(len(wins) / len(closed) * 100, 1) if closed else 0,
        "expectancy_R": round(total_R / len(closed), 3) if closed else 0,
        "total_R": round(total_R, 2),
        "by_session": by_session,
        "by_pair": by_pair,
        "recent": [
            {k: r.get(k) for k in ("pair", "signal", "session", "grade", "risk_reward",
                                   "status", "R", "logged_at", "exit_at")}
            for r in records[-10:][::-1]
        ],
    }
