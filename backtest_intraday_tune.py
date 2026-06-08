"""
Desk-corrections tuning harness for the 15m intraday sweep-reversal engine.

    python backtest_intraday_tune.py

Pits the CURRENT engine (wick-tight stop, 2R target, all sessions, no quality filter)
against the principled corrections proposed at the desk, and lets the data decide:

  1. WIDER STOP   — the wick stop gets run by the double-tap; widen it (sl_atr_mult)
  2. LOWER RR     — a nearer target converts more often (min_rr)
  3. SESSION FOCUS— London-only (the one non-negative cell in the original test)
  4. REAL RAID    — only count a sweep that actually penetrates the pool (min_sweep_atr)
                    and/or only raid engineered equal-highs/lows (equal_pools_only)

Honest by construction: every number is NET of a 1.5-pip round-trip spread, and the
shortlisted configs are re-run OUT-OF-SAMPLE (older half vs unseen newer half) — a real
edge holds in BOTH halves; a curve-fit one doesn't. We are NOT grid-searching a hundred
combos (that just p-hacks noise); we test a handful of changes a trader would actually make.
"""

import sys

from app.config import INTRADAY_PAIRS
from app.smart_money.intraday_backtester import backtest_intraday_all, run_intraday_oos

COST = 1.5  # pip round-trip — realistic retail major spread

# label -> (description, filters passed to analyze_intraday)
CONFIGS = [
    ("baseline",      "sl x0.5  RR2.0  London+NY  no filter (ORIGINAL)",
        {"sl_atr_mult": 0.5, "min_rr": 2.0, "allowed_killzones": None}),
    ("wider_stop",    "sl x1.0  RR1.5  London+NY",
        {"sl_atr_mult": 1.0, "min_rr": 1.5}),
    ("wider_x15",     "sl x1.5  RR1.2  London+NY",
        {"sl_atr_mult": 1.5, "min_rr": 1.2}),
    ("london_only",   "sl x1.0  RR1.5  London ONLY",
        {"sl_atr_mult": 1.0, "min_rr": 1.5, "allowed_killzones": {"London Open"}}),
    ("real_raid",     "sl x1.0  RR1.5  London ONLY  sweep>=0.25ATR",
        {"sl_atr_mult": 1.0, "min_rr": 1.5, "allowed_killzones": {"London Open"}, "min_sweep_atr": 0.25}),
    ("equal_pools",   "sl x1.0  RR1.5  London ONLY  equal-H/L only",
        {"sl_atr_mult": 1.0, "min_rr": 1.5, "allowed_killzones": {"London Open"}, "equal_pools_only": True}),
]


def _pf(p):  # portfolio one-liner
    return (f"trades={p['total_trades']:>3}  win%={p['win_rate_pct']:>5}  "
            f"exp_R={p['expectancy_R']:>7}  totR={p['total_R']:>7}")


def _pair_line(r):
    if not r.get("trades"):
        return f"      {r.get('pair'):7} {r.get('note') or r.get('error') or 'no trades'}"
    kz = ""
    if r.get("by_killzone"):
        kz = "  | " + "  ".join(f"{k.split()[0]}:{v['R']}R/{v['trades']}" for k, v in r["by_killzone"].items())
    return (f"      {r['pair']:7} trades={r['trades']:>3} win%={r['win_rate_pct']:>5} "
            f"exp_R={r['expectancy_R']:>7} totR={r['total_R']:>7} PF={r.get('profit_factor')}{kz}")


def main():
    print("=" * 84)
    print(f"INTRADAY ENGINE — DESK CORRECTIONS  (15m, ~5000 bars/pair)  NET of {COST} pip spread")
    print(f"Pairs: {' '.join(INTRADAY_PAIRS)}")
    print("=" * 84)

    summary = []
    for label, desc, filters in CONFIGS:
        # gross for the baseline (to reproduce the known result); net for all.
        net = backtest_intraday_all(INTRADAY_PAIRS, cost_pips=COST, filters=filters)
        p = net["portfolio"]
        summary.append((label, p["expectancy_R"], p["total_R"], p["total_trades"]))
        print(f"\n[{label}]  {desc}")
        if label == "baseline":
            g = backtest_intraday_all(INTRADAY_PAIRS, cost_pips=0.0, filters=filters)["portfolio"]
            print(f"  GROSS  {_pf(g)}")
        print(f"  NET    {_pf(p)}")
        for r in net["by_pair"]:
            print(_pair_line(r))

    print("\n" + "=" * 84)
    print("RANKING by NET portfolio expectancy (R/trade):")
    for label, exp, tot, tr in sorted(summary, key=lambda x: x[1], reverse=True):
        flag = "  <-- positive" if exp > 0 else ""
        print(f"  {label:14} exp_R={exp:>7}  totR={tot:>7}  trades={tr:>3}{flag}")

    # Out-of-sample on the top NET config (only meaningful if it's positive).
    top = max(summary, key=lambda x: x[1])
    print("\n" + "=" * 84)
    print(f"OUT-OF-SAMPLE check on top config '[{top[0]}]' (older half vs unseen newer half, NET):")
    top_filters = dict(next(f for l, d, f in CONFIGS if l == top[0]))
    for pair in INTRADAY_PAIRS:
        oos = run_intraday_oos(pair, cost_pips=COST, filters=top_filters)
        if oos.get("error"):
            print(f"  {pair}: {oos['error']}")
            continue
        h1, h2 = oos["first_half"], oos["second_half"]
        print(f"  {pair}:  1st half {_half(h1)}   |   2nd half {_half(h2)}")


def _half(r):
    if not r.get("trades"):
        return "no trades"
    return f"exp_R={r['expectancy_R']} totR={r['total_R']} ({r['trades']}t {r['win_rate_pct']}%)"


if __name__ == "__main__":
    main()
