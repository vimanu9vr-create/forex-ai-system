"""
CLI backtest runner.

    python backtest.py              # all pairs, 1h, ~1500 bars
    python backtest.py EURUSD 4h    # one pair / timeframe

Replays the disciplined engine through Polygon history and prints win-rate,
expectancy (avg R per trade), profit factor, max drawdown, and win-rate per
confluence bucket. Expectancy > 0 = positive edge; profit_factor > 1 = profitable.
"""

import sys
import json

from app.smart_money.backtester import run_backtest, backtest_all


def main():
    args = sys.argv[1:]
    if args:
        pair = args[0].upper()
        interval = args[1] if len(args) > 1 else "1h"
        print(json.dumps(run_backtest(pair, interval), indent=2))
        return

    out = backtest_all()
    print("=" * 64)
    print("PORTFOLIO (all pairs):")
    print(json.dumps(out["portfolio"], indent=2))
    print("=" * 64)
    for r in out["by_pair"]:
        line = (f"{r.get('pair'):7} trades={r.get('trades',0):3} "
                f"win%={r.get('win_rate_pct','-')!s:5} "
                f"exp_R={r.get('expectancy_R','-')!s:7} "
                f"PF={r.get('profit_factor','-')!s:5} "
                f"maxDD_R={r.get('max_drawdown_R','-')!s:7} "
                f"{r.get('note') or r.get('error') or ''}")
        print(line)
        if r.get("by_confluence"):
            print(f"        by confluence: {r['by_confluence']}")


if __name__ == "__main__":
    main()
