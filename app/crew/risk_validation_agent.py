from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class RiskMetrics:
    """Risk assessment metrics"""
    var_95: float  # Value at Risk at 95% confidence
    max_drawdown: float
    position_risk: float  # Risk per position as % of account
    portfolio_risk: float  # Total portfolio risk as % of account
    correlation_risk: float  # Correlated position risk
    reward_risk_ratio: float


class RiskValidationAgent:
    """
    Specialized agent for pre-execution risk validation
    Prevents bad trades from executing based on risk parameters
    """

    def __init__(
        self,
        max_position_size: float = 2.0,  # Max % of account per trade
        max_portfolio_risk: float = 5.0,  # Max total portfolio risk %
        max_correlated_risk: float = 3.0,  # Max risk from correlated pairs
        min_reward_risk_ratio: float = 1.5,  # Min R:R ratio
    ):
        self.max_position_size = max_position_size
        self.max_portfolio_risk = max_portfolio_risk
        self.max_correlated_risk = max_correlated_risk
        self.min_reward_risk_ratio = min_reward_risk_ratio
        self.open_positions: Dict[str, Dict[str, Any]] = {}

    def validate_setup(
        self,
        pair: str,
        setup: Dict[str, Any],
        account_balance: float = 10000,
    ) -> Dict[str, Any]:
        """
        Validate a trade setup against risk parameters

        Args:
            pair: Currency pair (e.g., "EURUSD")
            setup: Trade setup with entry, stop_loss, take_profit
            account_balance: Current account balance

        Returns:
            Dict with validation result and risk metrics
        """
        validation_result = {
            "valid": True,
            "rejections": [],
            "warnings": [],
            "risk_metrics": None,
        }

        try:
            # Extract price levels
            entry = setup.get("entry_price", 0)
            stop_loss = setup.get("stop_loss", 0)
            take_profit = setup.get("take_profit", 0)

            if not entry or not stop_loss or not take_profit:
                validation_result["valid"] = False
                validation_result["rejections"].append("Missing price levels")
                return validation_result

            # Calculate position risk
            risk_pips = abs(entry - stop_loss)
            reward_pips = abs(take_profit - entry)

            # Check position size
            position_risk = (risk_pips / entry) * 100
            if position_risk > self.max_position_size:
                validation_result["valid"] = False
                validation_result["rejections"].append(
                    f"Position risk {position_risk:.2f}% exceeds max {self.max_position_size}%"
                )

            # Check reward/risk ratio
            if risk_pips > 0:
                reward_risk_ratio = reward_pips / risk_pips
                if reward_risk_ratio < self.min_reward_risk_ratio:
                    validation_result["valid"] = False
                    validation_result["rejections"].append(
                        f"R:R ratio {reward_risk_ratio:.2f} below minimum {self.min_reward_risk_ratio}"
                    )

            # Check portfolio risk
            total_portfolio_risk = self._calculate_portfolio_risk(pair, position_risk)
            if total_portfolio_risk > self.max_portfolio_risk:
                validation_result["valid"] = False
                validation_result["rejections"].append(
                    f"Portfolio risk {total_portfolio_risk:.2f}% exceeds max {self.max_portfolio_risk}%"
                )

            # Check correlation risk
            correlation_risk = self._calculate_correlation_risk(pair)
            if correlation_risk > self.max_correlated_risk:
                validation_result["warnings"].append(
                    f"High correlated position risk: {correlation_risk:.2f}%"
                )

            # Check for conflicting positions
            conflicts = self._check_position_conflicts(pair, setup)
            if conflicts:
                validation_result["warnings"].extend(conflicts)

            # Build risk metrics
            risk_metrics = RiskMetrics(
                var_95=position_risk * 0.95,
                max_drawdown=position_risk,
                position_risk=position_risk,
                portfolio_risk=total_portfolio_risk,
                correlation_risk=correlation_risk,
                reward_risk_ratio=reward_risk_ratio if risk_pips > 0 else 0,
            )
            validation_result["risk_metrics"] = risk_metrics

        except Exception as e:
            validation_result["valid"] = False
            validation_result["rejections"].append(f"Risk validation error: {str(e)}")

        return validation_result

    def add_open_position(self, pair: str, position: Dict[str, Any]):
        """Track an open position"""
        self.open_positions[pair] = position

    def close_position(self, pair: str):
        """Remove a closed position"""
        if pair in self.open_positions:
            del self.open_positions[pair]

    def get_open_positions(self) -> Dict[str, Dict[str, Any]]:
        """Get all open positions"""
        return self.open_positions.copy()

    def _calculate_portfolio_risk(self, pair: str, position_risk: float) -> float:
        """Calculate total portfolio risk including new position"""
        total_risk = position_risk

        # Add risk from open positions
        for open_pair, position in self.open_positions.items():
            if open_pair != pair:
                total_risk += position.get("risk", 0)

        return total_risk

    def _calculate_correlation_risk(self, pair: str) -> float:
        """Calculate risk from correlated pairs"""
        # Simplified correlation matrix (in production, use real correlations)
        correlations = {
            "EURUSD": ["GBPUSD", "USDCHF"],
            "GBPUSD": ["EURUSD", "EURGBP"],
            "USDCHF": ["EURUSD", "GBPUSD"],
            "USDJPY": ["NZDUSD"],
            "AUDUSD": ["NZDUSD"],
        }

        correlated_pairs = correlations.get(pair, [])
        correlated_risk = 0

        for open_pair in self.open_positions.keys():
            if open_pair in correlated_pairs:
                correlated_risk += self.open_positions[open_pair].get("risk", 0)

        return correlated_risk

    def _check_position_conflicts(self, pair: str, setup: Dict[str, Any]) -> list:
        """Check for conflicting positions"""
        conflicts = []

        if pair in self.open_positions:
            existing = self.open_positions[pair]
            setup_signal = setup.get("signal", "").lower()
            existing_signal = existing.get("signal", "").lower()

            # Check for opposite signals on same pair
            if setup_signal != existing_signal:
                conflicts.append(
                    f"Conflicting signal on {pair}: existing {existing_signal}, new {setup_signal}"
                )

        return conflicts

    def get_risk_summary(self) -> Dict[str, Any]:
        """Get risk summary for all open positions"""
        total_risk = sum(p.get("risk", 0) for p in self.open_positions.values())

        return {
            "open_positions": len(self.open_positions),
            "total_portfolio_risk": total_risk,
            "max_allowed_risk": self.max_portfolio_risk,
            "risk_available": max(0, self.max_portfolio_risk - total_risk),
            "positions": list(self.open_positions.keys()),
        }
