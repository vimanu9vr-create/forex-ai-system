"""
AdaptiveAgent — Dynamically adjusts setup confidence based on recent performance.

Uses reflection data to scale up or down confidence scores, ensuring the system
becomes more conservative after losses and more aggressive after winning streaks.
"""


class AdaptiveAgent:

    # Thresholds
    STRONG_WIN_RATE  = 0.70   # > 70% → boost confidence
    WEAK_WIN_RATE    = 0.50   # < 50% → reduce confidence
    ELITE_WIN_RATE   = 0.80   # > 80% → maximum boost
    DRAWDOWN_WIN_RATE = 0.35  # < 35% → hard reduce (drawdown protection)

    # Adjustment amounts
    BOOST_STRONG  =  5   # +5 when win rate > 70%
    BOOST_ELITE   =  8   # +8 when win rate > 80%
    REDUCE_WEAK   = -10  # -10 when win rate < 50%
    REDUCE_HARD   = -20  # -20 when win rate < 35%

    # Bounds
    MIN_CONFIDENCE = 0
    MAX_CONFIDENCE = 100

    def adjust_confidence(self, setup: dict, reflection: dict) -> dict:
        """
        Adjust setup confidence based on recent win rate from reflection data.

        Args:
            setup:      Setup dict containing 'confidence' or 'probability_score'
            reflection: Reflection dict containing 'win_rate' (0.0–1.0 scale)

        Returns:
            Adjusted copy of setup with updated confidence and adjustment metadata.
        """
        if not setup or not isinstance(setup, dict):
            return setup or {}

        adjusted = setup.copy()

        # Resolve confidence — support both field names
        original_confidence = float(
            adjusted.get("confidence")
            or adjusted.get("probability_score")
            or 0
        )

        # win_rate from ReflectionAgent is 0.0–1.0
        win_rate = float(reflection.get("win_rate", 0) if reflection else 0)
        total_trades = int(reflection.get("total_trades", 0) if reflection else 0)

        # Not enough data — don't adjust
        if total_trades < 3:
            adjusted["adaptive_note"] = f"Insufficient history ({total_trades} trades) — confidence unchanged"
            adjusted["confidence"] = original_confidence
            return adjusted

        # Calculate adjustment
        if win_rate >= self.ELITE_WIN_RATE:
            delta = self.BOOST_ELITE
            note = f"Elite win rate {win_rate*100:.0f}% → +{delta}"
        elif win_rate >= self.STRONG_WIN_RATE:
            delta = self.BOOST_STRONG
            note = f"Strong win rate {win_rate*100:.0f}% → +{delta}"
        elif win_rate <= self.DRAWDOWN_WIN_RATE:
            delta = self.REDUCE_HARD
            note = f"Drawdown win rate {win_rate*100:.0f}% → {delta} (protection mode)"
        elif win_rate < self.WEAK_WIN_RATE:
            delta = self.REDUCE_WEAK
            note = f"Weak win rate {win_rate*100:.0f}% → {delta}"
        else:
            delta = 0
            note = f"Neutral win rate {win_rate*100:.0f}% → no adjustment"

        new_confidence = max(
            self.MIN_CONFIDENCE,
            min(self.MAX_CONFIDENCE, original_confidence + delta)
        )

        adjusted["confidence"]         = new_confidence
        adjusted["probability_score"]  = new_confidence
        adjusted["adaptive_delta"]     = delta
        adjusted["adaptive_note"]      = note
        adjusted["win_rate_used"]      = win_rate
        adjusted["trades_analyzed"]    = total_trades

        print(f"[AdaptiveAgent] {note} | {original_confidence:.0f}% → {new_confidence:.0f}%")
        return adjusted

    def should_halt_trading(self, reflection: dict) -> tuple[bool, str]:
        """
        Circuit breaker: halt trading if performance is critically poor.
        Returns (should_halt, reason).
        """
        if not reflection:
            return False, ""

        win_rate    = float(reflection.get("win_rate", 1.0))
        total       = int(reflection.get("total_trades", 0))
        avg_pl      = float(reflection.get("average_profit_loss", 0))

        if total >= 5 and win_rate < 0.30:
            return True, f"Circuit breaker: win rate {win_rate*100:.0f}% across {total} trades"

        if total >= 3 and avg_pl < -50:
            return True, f"Circuit breaker: avg loss ${avg_pl:.2f} across {total} trades"

        return False, ""
