class RiskManager:
    def __init__(self, max_position_size=0.02, max_portfolio_risk=0.05, min_rr_ratio=1.5):
        self.max_position_size = max_position_size
        self.max_portfolio_risk = max_portfolio_risk
        self.min_rr_ratio = min_rr_ratio

    def validate_trade(self, setup: dict) -> dict:
        """
        Validate a trade setup against institutional risk parameters.
        Returns approved/rejected with full reasoning.

        Hard rejections (trade cannot proceed):
          - Probability < 80%
          - Missing entry/SL/TP prices
          - RR ratio < 1.5
          - Fewer than 2 smart money signals

        Soft warnings (logged but do not block):
          - No HTF bias field (may not always be populated)
        """
        confidence      = float(setup.get("confidence") or 0)
        probability     = float(setup.get("probability_score") or 0)
        effective_prob  = max(confidence, probability)

        entry_price  = setup.get("entry_price")
        stop_loss    = setup.get("stop_loss")
        take_profit  = setup.get("take_profit")

        rejections = []
        warnings   = []

        # ── Hard check 1: Probability ────────────────────────────────────
        if effective_prob < 80:
            rejections.append(
                f"Probability {effective_prob:.0f}% below 80% minimum"
            )

        # ── Hard check 2: Price levels present ───────────────────────────
        try:
            entry_f = float(entry_price or 0)
            sl_f    = float(stop_loss or 0)
            tp_f    = float(take_profit or 0)
            has_prices = entry_f > 0 and sl_f > 0 and tp_f > 0
        except (TypeError, ValueError):
            has_prices = False

        if not has_prices:
            rejections.append("Missing or invalid entry / stop-loss / take-profit levels")

        # ── Hard check 3: Risk/Reward ratio ──────────────────────────────
        rr_ratio = 0.0
        if has_prices:
            if entry_f > sl_f:           # Long
                risk   = entry_f - sl_f
                reward = tp_f - entry_f
            else:                        # Short
                risk   = sl_f - entry_f
                reward = entry_f - tp_f

            if risk > 0:
                rr_ratio = reward / risk
                if rr_ratio < self.min_rr_ratio:
                    rejections.append(
                        f"RR ratio {rr_ratio:.2f} below minimum {self.min_rr_ratio}"
                    )
            else:
                rejections.append("Invalid price levels — risk is zero or negative")

        # ── Hard check 4: Smart Money signals (min 2/4) ───────────────────
        sm_signals = sum([
            bool(setup.get("fvg_present")),
            bool(setup.get("order_blocks_present")),
            bool(setup.get("liquidity_confirmed")),
            bool(setup.get("sweeps_detected")),
        ])
        if sm_signals < 2:
            rejections.append(
                f"Only {sm_signals}/4 smart money signals — minimum 2 required"
            )

        # ── Soft warning: HTF bias ────────────────────────────────────────
        if not setup.get("higher_timeframe_bias"):
            warnings.append("No higher_timeframe_bias field — MTF alignment unconfirmed")

        # ── Decision ─────────────────────────────────────────────────────
        approved = len(rejections) == 0

        return {
            "approved":           approved,
            "message":            "Trade approved — all A+ criteria met" if approved
                                  else f"Trade rejected: {'; '.join(rejections)}",
            "confidence":         effective_prob,
            "rr_ratio":           round(rr_ratio, 2),
            "smart_money_signals": sm_signals,
            "risk_percentage":    1.0 if approved else 0.0,
            "rejections":         rejections,
            "warnings":           warnings,
        }
