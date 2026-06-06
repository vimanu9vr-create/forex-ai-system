"""
CLI runner for the 15m intraday sweep-reversal engine backtest.

    python backtest_intraday.py                 # EURUSD,GBPUSD,USDJPY — gross AND 1.5pip
    python backtest_intraday.py EURUSD 1.5       # one pair at a given round-trip cost

No-lookahead, limit-fill modelled, SL-before-TP conservative. `cost_pips` is the
round-trip spread deducted from every trade. The honest test: does the NET edge
survive a realistic retail spread (~1.5 pip on majors)?
"""

import sys
import json

from app.config import INTRADAY_PAIRS
from app.smart_money.intraday_backtester import run_intraday_backtest, backtest_intraday_all


def _line(r):
    return (f"{r.get('pair'):7} trades={r.get('trades', 0):3} "
            f"win%={r.get('win_rate_pct', '-')!s:5} "
            f"exp_R={r.get('expectancy_R', '-')!s:7} "
            f"PF={r.get('profit_factor', '-')!s:5} "
            f"totR={r.get('total_R', '-')!s:7} "
            f"maxDD={r.get('max_drawdown_R', '-')!s:7} "
            f"{r.get('note') or r.get('error') or ''}")


def main():
    args = sys.argv[1:]
    if args:
        pair = args[0].upper()
        cost = float(args[1]) if len(args) > 1 else 0.0
        print(json.dumps(run_intraday_backtest(pair, cost_pips=cost), indent=2))
        return

    for cost in (0.0, 1.5):
        label = "GROSS (no costs)" if cost == 0.0 else f"NET (cost {cost} pip round-trip)"
        out = backtest_intraday_all(INTRADAY_PAIRS, cost_pips=cost)
        print("=" * 72)
        print(f"15m INTRADAY ENGINE — {label}")
        print("PORTFOLIO:", json.dumps(out["portfolio"]))
        print("-" * 72)
        for r in out["by_pair"]:
            print(_line(r))
            if r.get("by_killzone"):
                print(f"        by killzone: {r['by_killzone']}")
        print()


if __name__ == "__main__":
    main()
