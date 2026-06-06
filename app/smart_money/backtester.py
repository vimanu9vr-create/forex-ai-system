"""
Backtester — replays historical candles through the disciplined dashboard engine
(stacked-MA trend filter + structure-based `trade_levels`) and simulates SL/TP
fills to measure whether the setup actually has an edge.

No lookahead: a setup is detected at the CLOSE of bar i (using only a trailing
window ending at i) and entered at that close; the outcome is walked forward from
bar i+1. Conservative: a bar touching both SL and TP counts as a loss.

`cost_pips` deducts a round-trip spread/commission cost from every trade (in R
terms, scaled by each trade's stop distance) so the NET edge can be measured.

History source: TwelveData has the deepest 1h forex history (up to 5000 bars);
Polygon's plan caps ~800 hourly bars. Volume isn't needed for price-based SL/TP
simulation, so the backtest uses the deepest OHLC source available. Fetched
history is cached in-process so multi-scenario runs don't re-hit the API.
"""

import time

import requests

from app.config import TWELVEDATA_API_KEY
from app.services.polygon_service import get_polygon_candles, is_configured as polygon_ok
from app.smart_money.live_pair_scanner import _trend_direction
from app.smart_money.risk_management import trade_levels

# Confluence inputs (same detectors the live scanner uses)
from app.smart_money.structure import detect_swings
from app.smart_money.liquidity import detect_equal_highs, detect_equal_lows
from app.smart_money.sweeps import detect_buy_side_sweeps, detect_sell_side_sweeps
from app.smart_money.choch import detect_bullish_choch, detect_bearish_choch
from app.smart_money.fvg import detect_fvg
from app.smart_money.order_blocks import detect_order_blocks
from app.smart_money.probability_engine import calculate_probability

DEFAULT_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"]
WINDOW = 160
_TD_INT = {"1h": "1h", "4h": "4h", "15min": "15min", "30min": "30min", "1day": "1day"}
_hist_cache: dict = {}


def _pip(pair):
    return 0.01 if "JPY" in pair.upper() else 0.0001


def _twelvedata_history(pair, interval, outputsize):
    if not TWELVEDATA_API_KEY:
        return []
    try:
        r = requests.get("https://api.twelvedata.com/time_series",
                         params={"symbol": f"{pair[:3]}/{pair[3:]}",
                                 "interval": _TD_INT.get(interval, "1h"),
                                 "outputsize": min(outputsize, 5000),
                                 "apikey": TWELVEDATA_API_KEY, "format": "JSON"},
                         timeout=30)
        d = r.json()
        if "values" not in d:
            return []
        return [{"datetime": v["datetime"], "open": float(v["open"]), "high": float(v["high"]),
                 "low": float(v["low"]), "close": float(v["close"]),
                 "volume": float(v.get("volume", 0) or 0)}
                for v in reversed(d["values"])]
    except Exception:
        return []


def _fetch_history(pair, interval, bars):
    """Deepest history (TwelveData first, Polygon fallback), cached in-process."""
    ck = (pair, interval, bars)
    if ck in _hist_cache:
        return _hist_cache[ck]
    td = _twelvedata_history(pair, interval, bars)
    series = td if len(td) >= 500 else (get_polygon_candles(pair, interval, bars) if polygon_ok() else td)
    _hist_cache[ck] = series
    return series


def _confluence_at(window, trend_confirmed) -> int:
    try:
        sw = detect_swings(window)
        zones = detect_equal_highs(sw["swing_highs"]) + detect_equal_lows(sw["swing_lows"])
        sweeps = detect_buy_side_sweeps(window, zones) + detect_sell_side_sweeps(window, zones)
        chb = detect_bullish_choch(window, sw["swing_highs"])
        chbe = detect_bearish_choch(window, sw["swing_lows"])
        fvg = detect_fvg(window)
        ob = detect_order_blocks(window)
        res = calculate_probability(
            sweeps={"swept": len(sweeps) > 0, "sweeps": sweeps},
            choch={"choch": len(chb) + len(chbe) > 0, "bullish": chb, "bearish": chbe},
            killzone={"active": False},
            multi_timeframe={"valid": trend_confirmed},
            fvg={"present": bool(fvg.get("bullish_fvg_zones") or fvg.get("bearish_fvg_zones"))},
            order_blocks={"present": bool(ob.get("bullish_order_blocks") or ob.get("bearish_order_blocks"))},
        )
        return int(res.get("probability_score", 0))
    except Exception:
        return 0


def _simulate(candles, i, side, entry, sl, tp, max_bars=400):
    for j in range(i + 1, min(len(candles), i + 1 + max_bars)):
        hi, lo = candles[j]["high"], candles[j]["low"]
        if side == "BUY":
            hit_sl, hit_tp = lo <= sl, hi >= tp
        else:
            hit_sl, hit_tp = hi >= sl, lo <= tp
        if hit_sl:
            return "loss", j, -1.0
        if hit_tp:
            return "win", j, abs(tp - entry) / abs(entry - sl)
    return "open", min(len(candles) - 1, i + max_bars), 0.0


def run_backtest(pair="EURUSD", interval="1h", bars=5000, warmup=WINDOW, cost_pips=0.0):
    candles = _fetch_history(pair, interval, bars)
    if not candles or len(candles) < warmup + 50:
        return {"pair": pair, "error": "insufficient data", "trades": 0, "candles": len(candles or [])}

    pip = _pip(pair)
    trades = []
    i = warmup
    n = len(candles)
    while i < n - 2:
        window = candles[i - WINDOW + 1:i + 1]
        direction = _trend_direction(window)
        if direction in ("buy", "sell"):
            lv = trade_levels(pair, direction, window)
            if lv.get("valid"):
                side = "BUY" if direction == "buy" else "SELL"
                entry, sl, tp = lv["entry_price"], lv["stop_loss"], lv["take_profit"]
                result, exit_i, R = _simulate(candles, i, side, entry, sl, tp)
                if result != "open":
                    risk_price = abs(entry - sl)
                    cost_R = (cost_pips * pip) / risk_price if (cost_pips and risk_price > 0) else 0.0
                    trades.append({"R": R - cost_R, "result": result, "bars": exit_i - i,
                                   "confluence": _confluence_at(window, True)})
                    i = exit_i + 1
                    continue
        i += 1

    return _summarize(pair, trades, n)


def _bucket_winrate(trades):
    buckets = {"<60": [], "60-79": [], ">=80": []}
    for t in trades:
        c = t["confluence"]
        key = "<60" if c < 60 else ("60-79" if c < 80 else ">=80")
        buckets[key].append(t)
    out = {}
    for k, ts in buckets.items():
        if ts:
            wr = sum(1 for t in ts if t["result"] == "win") / len(ts) * 100
            out[k] = {"trades": len(ts), "win_rate_pct": round(wr, 1),
                      "expectancy_R": round(sum(t["R"] for t in ts) / len(ts), 3)}
    return out


def _summarize(pair, trades, n_candles):
    if not trades:
        return {"pair": pair, "trades": 0, "note": "no setups in window", "candles": n_candles}
    wins = [t for t in trades if t["result"] == "win"]
    losses = [t for t in trades if t["result"] == "loss"]
    total_R = sum(t["R"] for t in trades)
    gross_win = sum(t["R"] for t in wins if t["R"] > 0)
    gross_loss = -sum(t["R"] for t in trades if t["R"] < 0)

    eq = peak = maxdd = 0.0
    for t in trades:
        eq += t["R"]; peak = max(peak, eq); maxdd = min(maxdd, eq - peak)

    return {
        "pair": pair,
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(len(wins) / len(trades) * 100, 1),
        "expectancy_R": round(total_R / len(trades), 3),
        "total_R": round(total_R, 2),
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else None,
        "max_drawdown_R": round(maxdd, 2),
        "avg_bars_held": round(sum(t["bars"] for t in trades) / len(trades), 1),
        "by_confluence": _bucket_winrate(trades),
        "candles": n_candles,
    }


def backtest_all(pairs=None, interval="1h", bars=5000, cost_pips=0.0):
    pairs = pairs or DEFAULT_PAIRS
    results = []
    for idx, p in enumerate(pairs):
        results.append(run_backtest(p, interval, bars, cost_pips=cost_pips))
        if idx < len(pairs) - 1 and (p, interval, bars) not in _hist_cache:
            time.sleep(2)
    closed = [r for r in results if r.get("trades")]
    tt = sum(r["trades"] for r in closed)
    tw = sum(r["wins"] for r in closed)
    tR = sum(r["total_R"] for r in closed)
    portfolio = {
        "interval": interval,
        "cost_pips": cost_pips,
        "total_trades": tt,
        "win_rate_pct": round(tw / tt * 100, 1) if tt else 0,
        "expectancy_R": round(tR / tt, 3) if tt else 0,
        "total_R": round(tR, 2),
    }
    return {"portfolio": portfolio, "by_pair": results}
