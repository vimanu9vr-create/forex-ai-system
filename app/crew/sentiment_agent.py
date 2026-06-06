from typing import Dict, Any, Optional
from enum import Enum


class MarketSentiment(Enum):
    STRONGLY_BULLISH = "strongly_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    STRONGLY_BEARISH = "strongly_bearish"


class SentimentAgent:
    """
    Specialized agent for market sentiment analysis
    Validates setups against market sentiment and bias
    """

    def __init__(self):
        self.pair_sentiment: Dict[str, Dict[str, Any]] = {}
        self.session_biases: Dict[str, str] = {}  # Market session biases

    def analyze_setup_sentiment(
        self,
        pair: str,
        setup: Dict[str, Any],
        market_bias: Optional[str] = None,
        session: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze sentiment alignment with trade setup

        Args:
            pair: Currency pair
            setup: Trade setup with signal and probability
            market_bias: Overall market bias (bullish/bearish/neutral)
            session: Trading session (london/newyork/tokyo/sydney)

        Returns:
            Sentiment analysis with alignment score
        """
        analysis = {
            "valid": True,
            "sentiment_alignment": 0.0,
            "confirmations": [],
            "warnings": [],
            "pair_sentiment": None,
            "session_bias": None,
            "divergence_detected": False,
        }

        try:
            # Normalize signal: setups emit BUY/SELL, sentiment keys off bullish/bearish
            _raw_signal = setup.get("signal", "").lower()
            signal = ("bullish" if _raw_signal in ("buy", "long", "bullish")
                      else "bearish" if _raw_signal in ("sell", "short", "bearish")
                      else _raw_signal)
            probability = setup.get("probability_score", 50)

            # Get pair sentiment
            pair_sentiment_data = self._get_pair_sentiment(pair)
            analysis["pair_sentiment"] = pair_sentiment_data

            # Get session bias
            session_bias = self._get_session_bias(session)
            analysis["session_bias"] = session_bias

            # Check alignment with pair sentiment
            sentiment_alignment = self._check_sentiment_alignment(
                signal, pair_sentiment_data, market_bias
            )
            analysis["sentiment_alignment"] = sentiment_alignment["score"]

            if sentiment_alignment["aligned"]:
                analysis["confirmations"].append(sentiment_alignment["reason"])
            else:
                analysis["warnings"].append(sentiment_alignment["reason"])

            # Check session bias alignment
            session_alignment = self._check_session_alignment(signal, session_bias)
            if session_alignment["aligned"]:
                analysis["confirmations"].append(session_alignment["reason"])
            else:
                analysis["warnings"].append(session_alignment["reason"])

            # Check for divergence (price vs sentiment)
            divergence = self._check_divergence(pair, signal, pair_sentiment_data)
            if divergence["detected"]:
                analysis["divergence_detected"] = True
                analysis["warnings"].append(divergence["description"])
                analysis["valid"] = False
            else:
                analysis["confirmations"].append("No bearish/bullish divergence detected")

            # Adjust validity based on probability and sentiment
            if probability < 50:
                analysis["warnings"].append(f"Low probability setup ({probability}%)")
                analysis["valid"] = False

            if len(analysis["warnings"]) > 2:
                analysis["valid"] = False

        except Exception as e:
            analysis["valid"] = False
            analysis["warnings"].append(f"Sentiment analysis error: {str(e)}")

        return analysis

    def _get_pair_sentiment(self, pair: str) -> Dict[str, Any]:
        """Get sentiment data for a pair"""
        if pair in self.pair_sentiment:
            return self.pair_sentiment[pair]

        # Default neutral sentiment
        return {
            "sentiment": MarketSentiment.NEUTRAL.value,
            "strength": 50,  # 0-100
            "recent_trend": "sideways",
            "volume_profile": "neutral",
        }

    def _get_session_bias(self, session: Optional[str]) -> Dict[str, Any]:
        """Get market session bias"""
        session_biases = {
            "tokyo": {"bias": "bullish", "strength": 40, "active_pairs": ["USDJPY", "AUDUSD"]},
            "london": {"bias": "bullish", "strength": 70, "active_pairs": ["EURUSD", "GBPUSD"]},
            "newyork": {"bias": "bullish", "strength": 80, "active_pairs": ["EURUSD", "GBPUSD"]},
            "sydney": {"bias": "bearish", "strength": 60, "active_pairs": ["AUDUSD", "NZDUSD"]},
        }

        return session_biases.get(session.lower() if session else "london",
                                  {"bias": "neutral", "strength": 50, "active_pairs": []})

    def _check_sentiment_alignment(
        self,
        signal: str,
        sentiment_data: Dict[str, Any],
        market_bias: Optional[str],
    ) -> Dict[str, Any]:
        """Check if signal aligns with sentiment"""
        sentiment = sentiment_data.get("sentiment", MarketSentiment.NEUTRAL.value)
        strength = sentiment_data.get("strength", 50)

        aligned = False
        reason = ""

        if signal == "bullish":
            if "bullish" in sentiment:
                aligned = True
                reason = f"Setup bullish, aligned with {sentiment} sentiment (strength: {strength}%)"
            elif market_bias == "bullish":
                aligned = True
                reason = f"Setup bullish, confirmed by market bias"
        elif signal == "bearish":
            if "bearish" in sentiment:
                aligned = True
                reason = f"Setup bearish, aligned with {sentiment} sentiment (strength: {strength}%)"
            elif market_bias == "bearish":
                aligned = True
                reason = f"Setup bearish, confirmed by market bias"

        if not aligned:
            reason = f"Setup {signal} appears misaligned with {sentiment} sentiment"

        return {
            "aligned": aligned,
            "reason": reason,
            "score": strength if aligned else max(0, 100 - strength),
        }

    def _check_session_alignment(
        self,
        signal: str,
        session_bias: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check if signal aligns with session bias"""
        session_bias_val = session_bias.get("bias", "neutral")
        strength = session_bias.get("strength", 50)

        aligned = False
        reason = ""

        if signal == "bullish" and "bullish" in session_bias_val:
            aligned = True
            reason = f"Signal bullish, aligned with session bias (strength: {strength}%)"
        elif signal == "bearish" and "bearish" in session_bias_val:
            aligned = True
            reason = f"Signal bearish, aligned with session bias (strength: {strength}%)"
        else:
            reason = f"Signal {signal} may contradict session bias {session_bias_val}"

        return {
            "aligned": aligned,
            "reason": reason,
        }

    def _check_divergence(
        self,
        pair: str,
        signal: str,
        sentiment_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check for price vs sentiment divergence"""
        sentiment = sentiment_data.get("sentiment", MarketSentiment.NEUTRAL.value)
        recent_trend = sentiment_data.get("recent_trend", "sideways")

        divergence_detected = False
        description = ""

        # Bullish price action with bearish sentiment = bullish divergence
        if signal == "bullish" and "bearish" in sentiment:
            divergence_detected = True
            description = "Bullish divergence: Price shows bullish setup despite bearish sentiment - Potential strong move"

        # Bearish price action with bullish sentiment = bearish divergence
        elif signal == "bearish" and "bullish" in sentiment:
            divergence_detected = True
            description = "Bearish divergence: Price shows bearish setup despite bullish sentiment - Potential reversal"

        return {
            "detected": divergence_detected,
            "description": description,
        }

    def update_pair_sentiment(
        self,
        pair: str,
        sentiment: str,
        strength: int = 50,
        trend: str = "sideways",
        volume_profile: str = "neutral",
    ):
        """Update sentiment data for a pair"""
        self.pair_sentiment[pair] = {
            "sentiment": sentiment,
            "strength": min(100, max(0, strength)),
            "recent_trend": trend,
            "volume_profile": volume_profile,
        }

    def update_session_bias(self, session: str, bias: str):
        """Update bias for a trading session"""
        self.session_biases[session.lower()] = bias

    def get_market_overview(self) -> Dict[str, Any]:
        """Get overview of market sentiment"""
        bullish_pairs = [
            p for p, data in self.pair_sentiment.items() if "bullish" in data.get("sentiment", "")
        ]
        bearish_pairs = [
            p for p, data in self.pair_sentiment.items() if "bearish" in data.get("sentiment", "")
        ]

        return {
            "total_pairs_tracked": len(self.pair_sentiment),
            "bullish_pairs": bullish_pairs,
            "bearish_pairs": bearish_pairs,
            "session_biases": self.session_biases,
        }

    def get_pair_sentiment_score(self, pair: str) -> float:
        """Get sentiment score for a pair (0-100, 50=neutral)"""
        if pair not in self.pair_sentiment:
            return 50.0

        sentiment_data = self.pair_sentiment[pair]
        sentiment = sentiment_data.get("sentiment", MarketSentiment.NEUTRAL.value)
        strength = sentiment_data.get("strength", 50)

        if "bullish" in sentiment:
            return strength
        elif "bearish" in sentiment:
            return 100 - strength
        else:
            return 50.0
