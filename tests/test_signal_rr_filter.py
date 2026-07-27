"""Tests for the dashboard reward:risk display floor in app.services.signal_service.

Covers the rr_ratio_value parser and build_signal_from_scan's rule that
directional setups below DISPLAY_MIN_RR (e.g. 1:0.4) are dropped even in
show_all mode, while healthy-RR setups and HOLD rows are kept.

Runnable two ways:
    pytest tests/test_signal_rr_filter.py
    python tests/test_signal_rr_filter.py      # no pytest required
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.signal_service import build_signal_from_scan, rr_ratio_value


def _candles(close, high=1.1100, low=1.0900):
    """20 candles establishing a fixed swing high/low, last close = `close`."""
    body = [{"open": 1.10, "high": high, "low": low, "close": 1.10} for _ in range(19)]
    body.append({"open": close, "high": close + 0.0005, "low": close - 0.0005, "close": close})
    return body


def test_rr_parser_handles_ratio_string():
    assert rr_ratio_value("1:2.5") == 2.5
    assert rr_ratio_value("1:0.4") == 0.4


def test_rr_parser_handles_number_and_bad_input():
    assert rr_ratio_value(3) == 3.0
    assert rr_ratio_value("1.5") == 1.5
    assert rr_ratio_value("N/A") is None
    assert rr_ratio_value(None) is None


def test_sub_1r_long_is_dropped_even_in_show_all():
    # Price near the swing high -> tiny reward, far stop -> RR < 1.
    scan = {"pair": "EURUSD", "direction": "BUY",
            "candles": _candles(close=1.1099), "confluence_score": 70}
    assert build_signal_from_scan(scan, show_all=True) is None


def test_healthy_rr_long_is_kept():
    # Price near the swing low -> large reward to the high, small risk -> RR >= 1.
    scan = {"pair": "EURUSD", "direction": "BUY",
            "candles": _candles(close=1.0902), "confluence_score": 80}
    sig = build_signal_from_scan(scan, show_all=True)
    assert sig is not None
    assert rr_ratio_value(sig["risk_reward"]) >= 1.0


def test_hold_row_is_unaffected():
    # No direction / no levels -> informational row, must still surface in show_all.
    scan = {"pair": "EURUSD", "direction": "HOLD", "candles": [], "confluence_score": 30}
    sig = build_signal_from_scan(scan, show_all=True)
    assert sig is not None
    assert sig["risk_reward"] == "N/A"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL  {t.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
