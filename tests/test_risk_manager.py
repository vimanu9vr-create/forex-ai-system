"""Unit tests for app.risk.risk_manager.RiskManager.validate_trade.

These cover the four hard-rejection rules (probability, price levels,
risk/reward ratio, smart-money signal count) plus the soft HTF-bias warning
and the long/short RR calculation.

Runnable two ways:
    pytest tests/test_risk_manager.py
    python tests/test_risk_manager.py      # no pytest required
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.risk.risk_manager import RiskManager


def _valid_long_setup(**overrides):
    """An A+ long setup that passes every hard check (RR = 2.0, 2 SM signals)."""
    setup = {
        "probability_score": 85,
        "entry_price": 1.1000,
        "stop_loss": 1.0950,        # risk  = 0.0050
        "take_profit": 1.1100,      # reward = 0.0100  -> RR 2.0
        "fvg_present": True,
        "order_blocks_present": True,
        "higher_timeframe_bias": "bullish",
    }
    setup.update(overrides)
    return setup


def test_valid_setup_is_approved():
    result = RiskManager().validate_trade(_valid_long_setup())
    assert result["approved"] is True
    assert result["rejections"] == []
    assert result["rr_ratio"] == 2.0
    assert result["smart_money_signals"] == 2


def test_low_probability_is_rejected():
    result = RiskManager().validate_trade(_valid_long_setup(probability_score=70))
    assert result["approved"] is False
    assert any("Probability" in r for r in result["rejections"])


def test_confidence_can_satisfy_probability():
    # No probability_score, but confidence >= 80 should still pass the prob gate.
    setup = _valid_long_setup()
    del setup["probability_score"]
    setup["confidence"] = 82
    result = RiskManager().validate_trade(setup)
    assert result["approved"] is True
    assert result["confidence"] == 82


def test_missing_prices_is_rejected():
    result = RiskManager().validate_trade(_valid_long_setup(entry_price=None))
    assert result["approved"] is False
    assert any("Missing or invalid" in r for r in result["rejections"])


def test_poor_risk_reward_is_rejected():
    # reward 0.0025 vs risk 0.0050 -> RR 0.5, below the 1.5 minimum.
    result = RiskManager().validate_trade(_valid_long_setup(take_profit=1.1025))
    assert result["approved"] is False
    assert result["rr_ratio"] == 0.5
    assert any("RR ratio" in r for r in result["rejections"])


def test_insufficient_smart_money_signals_is_rejected():
    setup = _valid_long_setup(order_blocks_present=False)  # only 1 signal left
    result = RiskManager().validate_trade(setup)
    assert result["approved"] is False
    assert result["smart_money_signals"] == 1
    assert any("smart money signals" in r for r in result["rejections"])


def test_short_setup_rr_is_computed_correctly():
    # Short: entry below stop. risk = 0.0050, reward = 0.0100 -> RR 2.0
    short = {
        "probability_score": 90,
        "entry_price": 1.1000,
        "stop_loss": 1.1050,
        "take_profit": 1.0900,
        "liquidity_confirmed": True,
        "sweeps_detected": True,
    }
    result = RiskManager().validate_trade(short)
    assert result["approved"] is True
    assert result["rr_ratio"] == 2.0


def test_missing_htf_bias_produces_soft_warning_only():
    setup = _valid_long_setup()
    del setup["higher_timeframe_bias"]
    result = RiskManager().validate_trade(setup)
    assert result["approved"] is True                       # warning does not block
    assert any("higher_timeframe_bias" in w for w in result["warnings"])


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
