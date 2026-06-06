"""
TradingOrchestrator — Coordinates all agents in the correct pipeline:

  1. MarketAgent     → scan pairs, find best A+ setup
  2. ReflectionAgent → analyze recent performance
  3. AdaptiveAgent   → adjust confidence based on performance
  4. ExecutionAgent  → validate and execute the adjusted setup

Includes circuit breaker: halts trading if performance is critically poor.
"""
from app.agents.market_agent import MarketAgent
from app.agents.execution_agent import ExecutionAgent
from app.agents.reflection_agent import ReflectionAgent
from app.agents.adaptive_agent import AdaptiveAgent


class TradingOrchestrator:

    # A+ minimum thresholds after adaptive adjustment
    MIN_CONFIDENCE_TO_TRADE = 80
    MIN_RR_TO_TRADE         = 1.5

    def __init__(self):
        self.market_agent     = MarketAgent()
        self.execution_agent  = ExecutionAgent()
        self.reflection_agent = ReflectionAgent()
        self.adaptive_agent   = AdaptiveAgent()

    def run(self) -> dict:
        """
        Full orchestrated pipeline:
          scan → reflect → adapt → execute
        """
        print("\n" + "═" * 60)
        print("🤖 TRADING ORCHESTRATOR — PIPELINE STARTED")
        print("═" * 60)

        # ── Step 1: Market Analysis ──────────────────────────────────────
        print("\n[1/4] Running market scan...")
        all_results = self.market_agent.analyze_market()

        if not all_results:
            return {
                "decision": "NO_TRADE",
                "reason":   "Market scanner returned no data (API or cache issue)",
            }

        # Find the best setup across all pairs
        best_setup = self._select_best_setup(all_results)

        if not best_setup:
            return {
                "decision":     "NO_TRADE",
                "reason":       "No setup meets A+ criteria from market scan",
                "pairs_scanned": len(all_results),
            }

        print(f"   ✅ Best setup: {best_setup.get('pair')} "
              f"{best_setup.get('signal')} @ {best_setup.get('probability_score', 0):.0f}%")

        # ── Step 2: Performance Reflection ──────────────────────────────
        print("\n[2/4] Analyzing recent performance...")
        performance = self.reflection_agent.analyze_performance()
        print(f"   Win rate: {performance.get('win_rate_pct', 0):.1f}% "
              f"over {performance.get('total_trades', 0)} trades")

        # ── Step 3: Circuit breaker ──────────────────────────────────────
        halt, halt_reason = self.adaptive_agent.should_halt_trading(performance)
        if halt:
            return {
                "decision":           "HALTED",
                "reason":             halt_reason,
                "performance":        performance,
                "recommendation":     performance.get("recommendation"),
            }

        # ── Step 4: Adaptive confidence adjustment ───────────────────────
        print("\n[3/4] Adjusting confidence adaptively...")
        adjusted_setup = self.adaptive_agent.adjust_confidence(best_setup, performance)
        adjusted_conf = adjusted_setup.get("confidence", 0)
        print(f"   Adjusted confidence: {adjusted_conf:.0f}%  "
              f"(delta: {adjusted_setup.get('adaptive_delta', 0):+d})")

        # Re-check threshold after adjustment
        if adjusted_conf < self.MIN_CONFIDENCE_TO_TRADE:
            return {
                "decision":        "NO_TRADE",
                "reason":          f"Confidence {adjusted_conf:.0f}% below threshold after adaptive adjustment",
                "original_setup":  best_setup,
                "adjusted_setup":  adjusted_setup,
                "performance":     performance,
                "adaptive_note":   adjusted_setup.get("adaptive_note"),
            }

        # ── Step 5: Execution ────────────────────────────────────────────
        print("\n[4/4] Executing trade...")
        trade_result = self.execution_agent.execute_trade(adjusted_setup)

        print("\n" + "═" * 60)
        print(f"✅ PIPELINE COMPLETE — {trade_result.get('status', 'UNKNOWN')}")
        print("═" * 60 + "\n")

        return {
            "decision":        trade_result.get("status", "UNKNOWN"),
            "pair":            adjusted_setup.get("pair"),
            "signal":          adjusted_setup.get("signal"),
            "confidence":      adjusted_conf,
            "adaptive_note":   adjusted_setup.get("adaptive_note"),
            "performance":     performance,
            "trade_result":    trade_result,
            "pairs_scanned":   len(all_results),
        }

    def _select_best_setup(self, results: list) -> dict | None:
        """
        From the market scan results, extract the single best A+ setup.
        Returns setup dict enriched with pair + smart money context,
        or None if nothing meets criteria.
        """
        best = None
        best_prob = 0

        for item in results:
            pair     = item.get("pair")
            fvg      = item.get("fvg", {}).get("present", False)
            ob       = item.get("order_blocks", {}).get("present", False)
            liq      = item.get("liquidity", {}).get("liquidity_confirmation", {}).get("confirmed", False)
            sweeps   = item.get("sweeps", {})
            swept    = len(sweeps.get("buy_side", []) + sweeps.get("sell_side", [])) > 0
            sm_count = sum([fvg, ob, liq, swept])
            kz       = item.get("killzone", {})

            for setup in item.get("setups", []):
                prob = float(setup.get("probability_score") or setup.get("confidence") or 0)
                rr   = float(setup.get("rr_ratio") or 0)

                # A+ gate
                if prob < self.MIN_CONFIDENCE_TO_TRADE:
                    continue
                if rr < self.MIN_RR_TO_TRADE:
                    continue
                if sm_count < 2:
                    continue

                if prob > best_prob:
                    best_prob = prob
                    best = {
                        **setup,
                        "pair":                   pair,
                        "probability_score":      prob,
                        "confidence":             prob,
                        "fvg_present":            fvg,
                        "order_blocks_present":   ob,
                        "liquidity_confirmed":    liq,
                        "sweeps_detected":        swept,
                        "killzone_active":        kz.get("active", False),
                        "session":                kz.get("info", {}).get("killzone", "N/A"),
                        "higher_timeframe_bias":  item.get("bias", {}).get("bias") if isinstance(item.get("bias"), dict) else str(item.get("bias", "")),
                        "smart_money_count":      sm_count,
                    }

        return best

    def get_status(self) -> dict:
        """Return current system status without executing a trade."""
        performance = self.reflection_agent.analyze_performance()
        halt, halt_reason = self.adaptive_agent.should_halt_trading(performance)
        return {
            "trading_active":  not halt,
            "halt_reason":     halt_reason if halt else None,
            "performance":     performance,
            "recommendation":  performance.get("recommendation"),
        }
