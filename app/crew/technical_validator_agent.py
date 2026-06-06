from typing import Dict, Any, List, Optional


class TechnicalValidatorAgent:
    """
    Specialized agent for technical pattern confirmation and validation
    Validates setups against key technical levels and confluence zones
    """

    def __init__(self):
        self.support_resistance_levels: Dict[str, List[float]] = {}
        self.confluenceZones: Dict[str, List[Dict[str, Any]]] = {}

    def validate_setup(
        self,
        pair: str,
        setup: Dict[str, Any],
        candles: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Validate a trade setup against technical levels

        Args:
            pair: Currency pair
            setup: Trade setup with entry, stop_loss, take_profit
            candles: Recent price candles for analysis

        Returns:
            Validation result with technical score
        """
        validation_result = {
            "valid": True,
            "technical_score": 0.0,
            "confirmations": [],
            "warnings": [],
            "key_levels": {},
        }

        try:
            entry = setup.get("entry_price", 0)
            stop_loss = setup.get("stop_loss", 0)
            take_profit = setup.get("take_profit", 0)
            # Normalize signal: setups emit BUY/SELL, this validator keys off bullish/bearish
            _raw_signal = setup.get("signal", "").lower()
            signal = ("bullish" if _raw_signal in ("buy", "long", "bullish")
                      else "bearish" if _raw_signal in ("sell", "short", "bearish")
                      else _raw_signal)

            if not all([entry, stop_loss, take_profit]):
                validation_result["valid"] = False
                return validation_result

            # Get key technical levels
            key_levels = self._identify_key_levels(pair, entry, candles)
            validation_result["key_levels"] = key_levels

            # Validate entry point against support/resistance
            entry_validation = self._validate_entry_point(pair, entry, signal, key_levels)
            if entry_validation["valid"]:
                validation_result["confirmations"].append(entry_validation["reason"])
            else:
                validation_result["warnings"].append(entry_validation["reason"])

            # Validate stop loss placement
            sl_validation = self._validate_stop_loss(pair, entry, stop_loss, signal, key_levels)
            if sl_validation["valid"]:
                validation_result["confirmations"].append(sl_validation["reason"])
            else:
                validation_result["warnings"].append(sl_validation["reason"])

            # Validate take profit placement
            tp_validation = self._validate_take_profit(pair, entry, take_profit, signal, key_levels)
            if tp_validation["valid"]:
                validation_result["confirmations"].append(tp_validation["reason"])
            else:
                validation_result["warnings"].append(tp_validation["reason"])

            # Check for confluence zones
            confluence_score = self._check_confluence(pair, entry, signal)
            validation_result["confluence_score"] = confluence_score

            # Calculate technical strength score
            confirmation_count = len(validation_result["confirmations"])
            warning_count = len(validation_result["warnings"])

            # Base score on confirmations and confluence
            technical_score = (confirmation_count * 25) + (confluence_score * 25)
            technical_score = min(100, technical_score)

            # Reduce score for warnings
            technical_score -= warning_count * 10

            validation_result["technical_score"] = max(0, technical_score)

            # Setup is valid if score >= 50 and no critical issues
            validation_result["valid"] = technical_score >= 50 and entry_validation["valid"]

        except Exception as e:
            validation_result["valid"] = False
            validation_result["warnings"].append(f"Technical validation error: {str(e)}")

        return validation_result

    def _identify_key_levels(
        self,
        pair: str,
        current_price: float,
        candles: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Identify key support and resistance levels"""
        key_levels = {
            "nearest_support": 0.0,
            "nearest_resistance": 0.0,
            "strong_support": [],
            "strong_resistance": [],
        }

        if not candles or len(candles) < 2:
            return key_levels

        # Find recent swing highs and lows
        highs = [c.get("high", 0) for c in candles[-50:]]
        lows = [c.get("low", 0) for c in candles[-50:]]

        if highs and lows:
            # Nearest resistance (highest high above current)
            resistances = [h for h in highs if h > current_price]
            if resistances:
                key_levels["nearest_resistance"] = min(resistances)
                key_levels["strong_resistance"] = resistances[:3]

            # Nearest support (lowest low below current)
            supports = [l for l in lows if l < current_price]
            if supports:
                key_levels["nearest_support"] = max(supports)
                key_levels["strong_support"] = supports[-3:]

        return key_levels

    def _validate_entry_point(
        self,
        pair: str,
        entry: float,
        signal: str,
        key_levels: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate entry point placement"""
        validation = {"valid": False, "reason": ""}

        if signal == "bullish":
            # For bullish, entry should be near support or above it
            nearest_support = key_levels.get("nearest_support", 0)
            if nearest_support > 0 and entry >= nearest_support * 0.999:
                validation["valid"] = True
                validation["reason"] = "Entry placed at/near support level - Bullish confirmation"
            else:
                validation["reason"] = "Entry not optimally placed relative to support"

        elif signal == "bearish":
            # For bearish, entry should be near resistance or below it
            nearest_resistance = key_levels.get("nearest_resistance", 0)
            if nearest_resistance > 0 and entry <= nearest_resistance * 1.001:
                validation["valid"] = True
                validation["reason"] = "Entry placed at/near resistance level - Bearish confirmation"
            else:
                validation["reason"] = "Entry not optimally placed relative to resistance"

        return validation

    def _validate_stop_loss(
        self,
        pair: str,
        entry: float,
        stop_loss: float,
        signal: str,
        key_levels: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate stop loss placement"""
        validation = {"valid": False, "reason": ""}

        if signal == "bullish":
            # For bullish, stop should be below entry and ideally below support
            if stop_loss < entry:
                nearest_support = key_levels.get("nearest_support", 0)
                if nearest_support > 0 and stop_loss < nearest_support:
                    validation["valid"] = True
                    validation["reason"] = "Stop loss placed below support - Good protection"
                else:
                    validation["valid"] = True
                    validation["reason"] = "Stop loss properly placed below entry"
            else:
                validation["reason"] = "Stop loss above entry - Invalid for bullish"

        elif signal == "bearish":
            # For bearish, stop should be above entry and ideally above resistance
            if stop_loss > entry:
                nearest_resistance = key_levels.get("nearest_resistance", 0)
                if nearest_resistance > 0 and stop_loss > nearest_resistance:
                    validation["valid"] = True
                    validation["reason"] = "Stop loss placed above resistance - Good protection"
                else:
                    validation["valid"] = True
                    validation["reason"] = "Stop loss properly placed above entry"
            else:
                validation["reason"] = "Stop loss below entry - Invalid for bearish"

        return validation

    def _validate_take_profit(
        self,
        pair: str,
        entry: float,
        take_profit: float,
        signal: str,
        key_levels: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate take profit placement"""
        validation = {"valid": False, "reason": ""}

        if signal == "bullish":
            # For bullish, TP should be above entry and ideally at resistance
            if take_profit > entry:
                nearest_resistance = key_levels.get("nearest_resistance", 0)
                if nearest_resistance > 0 and abs(take_profit - nearest_resistance) < entry * 0.01:
                    validation["valid"] = True
                    validation["reason"] = "Take profit at resistance level - Strong target"
                else:
                    validation["valid"] = True
                    validation["reason"] = "Take profit above entry"
            else:
                validation["reason"] = "Take profit below entry - Invalid for bullish"

        elif signal == "bearish":
            # For bearish, TP should be below entry and ideally at support
            if take_profit < entry:
                nearest_support = key_levels.get("nearest_support", 0)
                if nearest_support > 0 and abs(take_profit - nearest_support) < entry * 0.01:
                    validation["valid"] = True
                    validation["reason"] = "Take profit at support level - Strong target"
                else:
                    validation["valid"] = True
                    validation["reason"] = "Take profit below entry"
            else:
                validation["reason"] = "Take profit above entry - Invalid for bearish"

        return validation

    def _check_confluence(self, pair: str, entry: float, signal: str) -> float:
        """Check for confluence zones (multiple confirmations)"""
        # Simplified confluence checking
        # In production, would check for:
        # - MA intersections
        # - Fib levels
        # - Previous pivot points
        # - Volume profile

        confluence_score = 0.0

        # Base confluence from technical setup
        if pair in self.confluenceZones:
            for zone in self.confluenceZones[pair]:
                zone_low = zone.get("low", 0)
                zone_high = zone.get("high", 0)

                if zone_low <= entry <= zone_high:
                    confluence_score += 25.0

        # Default confluence if in range
        if 0 < entry < 100:  # Valid price range
            confluence_score = max(confluence_score, 25.0)

        return min(100.0, confluence_score)

    def register_confluence_zone(
        self,
        pair: str,
        low: float,
        high: float,
        zone_type: str = "support_resistance",
    ):
        """Register a confluence zone"""
        if pair not in self.confluenceZones:
            self.confluenceZones[pair] = []

        self.confluenceZones[pair].append(
            {
                "low": low,
                "high": high,
                "type": zone_type,
            }
        )

    def get_confluence_zones(self, pair: str) -> List[Dict[str, Any]]:
        """Get all confluence zones for a pair"""
        return self.confluenceZones.get(pair, [])

    def clear_old_zones(self, pair: str):
        """Clear old confluence zones"""
        if pair in self.confluenceZones:
            self.confluenceZones[pair] = []
