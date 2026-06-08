#!/usr/bin/env python
"""
Regression test for the dedicated 15m intraday liquidity-sweep engine.

Run: venv/bin/python test_intraday_engine.py

Covers:
  - killzone gating (UTC London/NY entry windows; Asian/off-session blocked)
  - a known sell-side-sweep -> bullish-displacement/MSS -> FVG entry fires a BUY
    with structurally-ordered SL < entry < TP and RR >= min
  - the killzone gate is the ONLY thing blocking an out-of-session sweep
"""
from datetime import datetime, timedelta

from app.config import INTRADAY_MIN_RR
from app.smart_money.killzones import in_killzone, is_entry_killzone
from app.smart_money.intraday_engine import analyze_intraday

# 25-bar sell-side-sweep -> bullish reversal, preceded by 40 low-range filler bars
# so the series clears MIN_CANDLES. (open, high, low, close) as pip-offsets from 1.1000.
PATH = [
    (60,64,57,62),(62,80,60,78),(78,92,76,88),(88,84,70,72),(72,74,55,58),
    (58,60,40,44),(44,46,28,32),(32,40,30,38),(38,48,36,46),(46,50,44,48),
    (48,58,46,56),(56,54,42,44),(44,46,30,33),(33,36,18,20),(20,24,12,14),
    (14,22,13,19),(19,21,15,17),(17,30,16,28),(28,34,24,26),(26,28,17,19),
    (19,22, 4,14),(24,30,24,29),(32,44,32,42),(42,43,30,33),(33,36,22,24),
]
FILLER = [(50 + (i % 6) - 3, 53 + (i % 6) - 3, 47 + (i % 6) - 3, 50 + (i % 6) - 3 + (1 if i % 2 else -1))
          for i in range(40)]
BASE = 1.1000


def build(start):
    """SERIES with the sweep bar (global idx 60) anchored relative to `start`."""
    series = FILLER + PATH
    return [{
        "datetime": (start + timedelta(minutes=15 * i)).strftime("%Y-%m-%d %H:%M:%S"),
        "open": round(BASE + o * 0.0001, 5), "high": round(BASE + h * 0.0001, 5),
        "low":  round(BASE + l * 0.0001, 5), "close": round(BASE + c * 0.0001, 5),
        "volume": 1000,
    } for i, (o, h, l, c) in enumerate(series)]


def test_killzones():
    assert is_entry_killzone("2024-01-02 08:30:00")        # London
    assert is_entry_killzone("2024-01-02 13:30:00")        # New York
    assert not is_entry_killzone("2024-01-02 03:30:00")    # Asian (no entries)
    assert not is_entry_killzone("2024-01-02 11:30:00")    # between sessions
    assert in_killzone("2024-01-02 08:30:00")["killzone"] == "London Open"
    print("ok  killzone gating")


def test_buy_fires_in_killzone():
    # START so the sweep bar (idx 60) = Jan-2 09:00 UTC -> inside London killzone
    sig = analyze_intraday("EURUSD", build(datetime(2024, 1, 1, 18, 0, 0)))
    assert sig is not None, "expected a BUY signal in the London killzone"
    assert sig["signal"] == "BUY"
    assert sig["stop_loss"] < sig["entry"] < sig["take_profit"]
    assert sig["risk_reward"] >= INTRADAY_MIN_RR   # configured floor (now 1.5 after the desk corrections)
    assert sig["entry_basis"] == "FVG"
    assert sig["killzone"] == "London Open"
    print(f"ok  BUY fires  entry={sig['entry']} sl={sig['stop_loss']} tp={sig['take_profit']} RR={sig['risk_reward']}")


def test_killzone_gate_blocks_off_session():
    # START so the sweep bar (idx 60) = Jan-2 11:00 UTC -> NOT a killzone
    candles = build(datetime(2024, 1, 1, 20, 0, 0))
    assert analyze_intraday("EURUSD", candles) is None, "off-session sweep must be gated out"
    # ...but the SAME setup fires when both session gates are disabled -> gating is the only blocker
    # (allowed_killzones now defaults to London-only, so pass None to isolate the entry-allowed gate)
    assert analyze_intraday("EURUSD", candles, require_killzone=False, allowed_killzones=None) is not None
    print("ok  killzone gate blocks off-session sweep (and only the gate)")


def test_htf_bias_hard_filter():
    c = build(datetime(2024, 1, 1, 18, 0, 0))  # a bullish sweep-reversal -> BUY
    assert analyze_intraday("EURUSD", c, htf_bias="bullish") is not None   # aligned -> fires
    assert analyze_intraday("EURUSD", c, htf_bias="bearish") is None       # counter-trend blocked
    assert analyze_intraday("EURUSD", c, htf_bias="neutral") is None       # mixed HTF -> stand aside
    s5 = analyze_intraday("EURUSD", c, htf_bias="bullish", tf="5min")
    assert s5 and s5["timeframe"] == "5min"                                # entry-TF label propagates
    print("ok  HTF bias hard-filter blocks counter-trend + neutral; tf label propagates")


if __name__ == "__main__":
    test_killzones()
    test_buy_fires_in_killzone()
    test_killzone_gate_blocks_off_session()
    test_htf_bias_hard_filter()
    print("\nAll intraday engine tests passed.")
