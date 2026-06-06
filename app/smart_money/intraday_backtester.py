"""
intraday_backtester — no-lookahead walk-forward of the dedicated 15m sweep-reversal
engine (intraday_engine.analyze_intraday), with LIMIT-FILL modeling and spread costs.

Why a separate backtester: the engine emits a LIMIT entry (a retracement into the
FVG/OTE), so a setup is only a trade if price actually trades back to the entry
within a few bars. We model that fill, then walk SL/TP forward.

No lookahead: at bar i the engine sees only candles[:i+1]; the entry fill and the
SL/TP outcome are simulated from bar i+1 onward. Conservative: a bar that touches
both SL and TP counts as a loss; `cost_pips` (round-trip spread) is deducted from
every trade's R so the NET edge is what's reported.

Run `python backtest_intraday.py` (root) for the standard gross-vs-costed report.
"""

from app.smart_money.backtester import _fetch_history, _pip
from app.smart_money.intraday_engine import analyze_intraday

WINDOW = 250        # bars of context fed to the engine (>= MIN_CANDLES)
FILL_BARS = 8       # limit entry must fill within ~2h or the setup is abandoned
MAX_BARS = 96       # max holding ~24h on 15m before marking the trade "open"


def _simulate_with_fill(candles, i, side, entry, sl, tp, pip, cost_pips):
    """Model limit fill then SL/TP. Returns a trade dict or None (never filled)."""
    n = len(candles)
    risk_price = abs(entry - sl)
    if risk_price <= 0:
        return None
    rr_target = abs(tp - entry) / risk_price

    fill_j = None
    for j in range(i + 1, min(n, i + 1 + FILL_BARS)):
        if (side == "BUY" and candles[j]["low"] <= entry) or \
           (side == "SELL" and candles[j]["high"] >= entry):
            fill_j = j
            break
    if fill_j is None:
        return None  # limit never filled -> no trade

    cost_R = (cost_pips * pip) / risk_price if cost_pips else 0.0
    for k in range(fill_j, min(n, fill_j + MAX_BARS)):
        hi, lo = candles[k]["high"], candles[k]["low"]
        if side == "BUY":
            hit_sl, hit_tp = lo <= sl, hi >= tp
        else:
            hit_sl, hit_tp = hi >= sl, lo <= tp
        if hit_sl:                                   # SL priority (conservative)
            return {"result": "loss", "R": -1.0 - cost_R, "exit": k}
        if hit_tp:
            return {"result": "win", "R": rr_target - cost_R, "exit": k}
    return {"result": "open", "R": 0.0, "exit": min(n - 1, fill_j + MAX_BARS)}


def run_intraday_backtest(pair, bars=5000, cost_pips=0.0, require_killzone=True, filters=None):
    filters = filters or {}
    candles = _fetch_history(pair, "15min", bars)
    if not candles or len(candles) < WINDOW + 50:
        return {"pair": pair, "error": "insufficient data", "trades": 0, "candles": len(candles or [])}

    pip = _pip(pair)
    trades = []
    i, n = WINDOW, len(candles)
    while i < n - 2:
        sig = analyze_intraday(pair, candles[i - WINDOW + 1:i + 1], require_killzone=require_killzone, **filters)
        if sig and sig["signal"] in ("BUY", "SELL"):
            res = _simulate_with_fill(candles, i, sig["signal"], sig["entry"],
                                      sig["stop_loss"], sig["take_profit"], pip, cost_pips)
            if res and res["result"] != "open":
                res["killzone"] = sig["killzone"]
                trades.append(res)
                i = res["exit"] + 1
                continue
            i += FILL_BARS + 1   # never filled (or still open) -> skip past this setup
            continue
        i += 1

    return _summarize(pair, trades, n, cost_pips)


def _summarize(pair, trades, n_candles, cost_pips):
    if not trades:
        return {"pair": pair, "trades": 0, "note": "no setups filled", "candles": n_candles}
    wins = [t for t in trades if t["result"] == "win"]
    total_R = sum(t["R"] for t in trades)
    gross_win = sum(t["R"] for t in wins if t["R"] > 0)
    gross_loss = -sum(t["R"] for t in trades if t["R"] < 0)

    eq = peak = maxdd = 0.0
    for t in trades:
        eq += t["R"]; peak = max(peak, eq); maxdd = min(maxdd, eq - peak)

    kz = {}
    for t in trades:
        b = kz.setdefault(t.get("killzone", "?"), {"trades": 0, "wins": 0, "R": 0.0})
        b["trades"] += 1; b["wins"] += 1 if t["result"] == "win" else 0; b["R"] += t["R"]
    for b in kz.values():
        b["win_rate_pct"] = round(b["wins"] / b["trades"] * 100, 1)
        b["R"] = round(b["R"], 2)

    return {
        "pair": pair,
        "cost_pips": cost_pips,
        "trades": len(trades),
        "win_rate_pct": round(len(wins) / len(trades) * 100, 1),
        "expectancy_R": round(total_R / len(trades), 3),
        "total_R": round(total_R, 2),
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else None,
        "max_drawdown_R": round(maxdd, 2),
        "by_killzone": kz,
        "candles": n_candles,
    }


def backtest_intraday_all(pairs, bars=5000, cost_pips=0.0, filters=None):
    results = [run_intraday_backtest(p, bars=bars, cost_pips=cost_pips, filters=filters) for p in pairs]
    closed = [r for r in results if r.get("trades")]
    tt = sum(r["trades"] for r in closed)
    tR = sum(r["total_R"] for r in closed)
    tw = sum(round(r["win_rate_pct"] / 100 * r["trades"]) for r in closed)
    return {
        "portfolio": {
            "cost_pips": cost_pips,
            "total_trades": tt,
            "win_rate_pct": round(tw / tt * 100, 1) if tt else 0,
            "expectancy_R": round(tR / tt, 3) if tt else 0,
            "total_R": round(tR, 2),
        },
        "by_pair": results,
    }
