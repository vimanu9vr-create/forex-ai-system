"""
CrewAI tool definitions.

Each @tools.tool function is called by CrewAI agents during task execution.
Tools wrap the underlying Python agents with error handling and logging.
"""
import time
import uuid
from typing import Optional

from crewai import tools

from app.agents.market_agent import MarketAgent
from app.agents.reflection_agent import ReflectionAgent
from app.agents.execution_agent import ExecutionAgent
from app.crew.error_handler import error_metrics
from app.crew.crew_logger import crew_logger
from app.crew.agent_manager import agent_manager
from app.services.telegram_service import send_elite_setup_alert
from app.config import MIN_RISK_REWARD

# ── Singleton agent instances ─────────────────────────────────────────────
_market_agent    = MarketAgent()
_reflection_agent = ReflectionAgent()
_execution_agent  = ExecutionAgent()

# Register with manager for health tracking
agent_manager.register_agent("market_analyst",    _market_agent)
agent_manager.register_agent("reflection_analyst", _reflection_agent)
agent_manager.register_agent("execution_engine",   _execution_agent)


# ── Tool 1: Market Analysis ───────────────────────────────────────────────
@tools.tool
def analyze_market() -> list:
    """
    Scan all configured forex pairs (EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD,
    NZDUSD, USDCHF) using institutional Smart Money analysis.

    Returns a ranked list of setups. Each setup contains:
      pair, direction, probability_score, entry/sl/tp levels,
      fvg_present, order_blocks_present, liquidity_confirmed,
      sweeps_detected, killzone_active, rr_ratio, timeframe, session.

    Select the single setup with the highest probability_score that passes
    all A+ criteria (prob >= 80, smart_money >= 2/4, RR >= 1.5).
    """
    start_time = time.time()
    cid = str(uuid.uuid4())[:8]

    try:
        agent_manager.notify_agent_started(
            agent_name="market_analyst",
            source_agent="crew",
            target_agents=["execution_engine"],
            data={"op": "analyze_market"},
            correlations_id=cid,
        )

        # Direct call — market_agent.analyze_market() returns list
        results = _market_agent.analyze_market()

        elapsed = time.time() - start_time
        agent_manager.record_execution(
            agent_name="market_analyst",
            task_name="market_analysis",
            success=True,
            execution_time=elapsed,
            result=f"{len(results)} pairs scanned",
        )
        crew_logger.log_agent_execution(
            agent_name="market_analyst",
            task="market_analysis",
            status="success",
            execution_time=elapsed,
        )

        # Build compact summary for CrewAI context (avoid huge payloads)
        summaries = []
        for r in results:
            pair = r.get("pair", "?")
            prob = r.get("probability_score", 0)
            direction = "N/A"
            bias = r.get("bias", {})
            if isinstance(bias, dict):
                bias_val = bias.get("bias", "neutral").lower()
                direction = "BUY" if bias_val == "bullish" else "SELL" if bias_val == "bearish" else "HOLD"

            setups = r.get("setups", [])
            best_setup = max(setups, key=lambda s: s.get("confidence", 0), default={}) if setups else {}

            summaries.append({
                "pair": pair,
                "direction": direction,
                "probability_score": prob,
                "entry_price":   best_setup.get("entry_price"),
                "stop_loss":     best_setup.get("stop_loss"),
                "take_profit":   best_setup.get("take_profit"),
                "rr_ratio":      best_setup.get("rr_ratio", 0),
                "confidence":    best_setup.get("confidence", prob),
                "timeframe":     best_setup.get("timeframe") or r.get("timeframe"),
                "fvg_present":            r.get("fvg", {}).get("present", False),
                "order_blocks_present":   r.get("order_blocks", {}).get("present", False),
                "liquidity_confirmed":    r.get("liquidity", {}).get("liquidity_confirmation", {}).get("confirmed", False),
                "sweeps_detected":        len((r.get("sweeps") or {}).get("buy_side", []) +
                                              (r.get("sweeps") or {}).get("sell_side", [])) > 0,
                "killzone_active":        r.get("killzone", {}).get("active", False),
                "session":                r.get("killzone", {}).get("info", {}).get("killzone", "N/A"),
                "higher_timeframe_bias":  r.get("htf_bias", "neutral"),
                "bos_confirmed":          bool((r.get("bos") or {}).get("bullish") or (r.get("bos") or {}).get("bearish")),
                "choch_confirmed":        bool((r.get("choch") or {}).get("bullish") or (r.get("choch") or {}).get("bearish")),
                "invalidation":           best_setup.get("stop_loss"),
                "poc":                    (r.get("market_profile") or {}).get("poc"),
                "value_area_high":        (r.get("market_profile") or {}).get("vah"),
                "value_area_low":         (r.get("market_profile") or {}).get("val"),
                "wyckoff_phase":          (r.get("wyckoff") or {}).get("phase"),
                "wyckoff_bias":           (r.get("wyckoff") or {}).get("bias"),
                "macro_event_risk":       (r.get("macro") or {}).get("event_risk"),
                "macro_high_impact":      [e.get("event") for e in (r.get("macro") or {}).get("high_impact_events", [])][:3],
                "macro_headlines":        (r.get("macro") or {}).get("headlines", [])[:2],
                "analysis_notes":         best_setup.get("analysis_notes", ""),
            })

        summaries.sort(key=lambda s: s["probability_score"], reverse=True)
        return summaries

    except Exception as e:
        elapsed = time.time() - start_time
        error_metrics.record_error("analyze_market", e)
        crew_logger.log_error(
            error_type="tool_error",
            agent_name="market_analyst",
            error_message=str(e),
        )
        agent_manager.record_execution(
            agent_name="market_analyst",
            task_name="market_analysis",
            success=False,
            execution_time=elapsed,
            error=e,
        )
        print(f"[analyze_market] Error: {e}")
        return []


# ── Tool 2: Performance Analysis ─────────────────────────────────────────
@tools.tool
def analyze_performance() -> dict:
    """
    Analyze recent trade performance from the trade memory store.

    Returns win rate, trade count, P&L, and qualitative pattern analysis
    to help validate whether the current proposed setup matches historical
    winning conditions.
    """
    start_time = time.time()
    cid = str(uuid.uuid4())[:8]

    try:
        agent_manager.notify_agent_started(
            agent_name="reflection_analyst",
            source_agent="crew",
            target_agents=[],
            data={"op": "analyze_performance"},
            correlations_id=cid,
        )

        result = _reflection_agent.analyze_performance()

        elapsed = time.time() - start_time
        agent_manager.record_execution(
            agent_name="reflection_analyst",
            task_name="performance_analysis",
            success=True,
            execution_time=elapsed,
        )
        return result

    except Exception as e:
        elapsed = time.time() - start_time
        error_metrics.record_error("analyze_performance", e)
        print(f"[analyze_performance] Error: {e}")
        return {
            "message": "Performance data unavailable",
            "win_rate": 0,
            "total_trades": 0,
        }


# ── Tool 3: Trade Execution ───────────────────────────────────────────────
@tools.tool
def execute_trade(setup: dict) -> dict:
    """
    Execute a validated A+ trade setup through the execution engine.

    Pass the complete setup dict from the market analyst. The tool will:
    1. Validate probability >= 80% and RR >= 1.5
    2. Run risk manager checks
    3. Save trade to database
    4. Send Telegram A+ alert

    Returns execution result with status (EXECUTED/REJECTED) and trade details.

    Required fields in setup:
      pair, signal, entry_price, stop_loss, take_profit, probability_score,
      rr_ratio, fvg_present, order_blocks_present, liquidity_confirmed,
      sweeps_detected, session, timeframe, analysis_notes
    """
    start_time = time.time()
    cid = str(uuid.uuid4())[:8]

    if not setup or not isinstance(setup, dict):
        return {"status": "REJECTED", "reason": "No valid setup dict provided to execute_trade"}

    pair  = setup.get("pair", "N/A")
    signal = setup.get("signal", "N/A")
    prob  = float(setup.get("probability_score") or setup.get("confidence") or 0)
    rr    = float(setup.get("rr_ratio") or 0)

    # Hard A+ gate before even calling execution agent
    if prob < 80:
        return {
            "status": "REJECTED",
            "pair": pair,
            "reason": f"Probability {prob:.0f}% below 80% minimum threshold",
        }
    if rr < MIN_RISK_REWARD:
        return {
            "status": "REJECTED",
            "pair": pair,
            "reason": f"RR ratio {rr:.2f} below {MIN_RISK_REWARD} minimum",
        }

    try:
        agent_manager.notify_agent_started(
            agent_name="execution_engine",
            source_agent="crew",
            target_agents=[],
            data={"op": "execute_trade", "pair": pair, "signal": signal},
            correlations_id=cid,
        )

        result = _execution_agent.execute_trade(setup)
        elapsed = time.time() - start_time

        agent_manager.record_execution(
            agent_name="execution_engine",
            task_name="trade_execution",
            success=result.get("status") in ("SUCCESS", "EXECUTED"),
            execution_time=elapsed,
        )

        # Send elite Telegram alert on successful execution
        if result.get("status") in ("SUCCESS", "EXECUTED"):
            smart_money = {
                "fvg_present":         setup.get("fvg_present", False),
                "order_blocks":        setup.get("order_blocks_present", False),
                "liquidity_confirmed": setup.get("liquidity_confirmed", False),
                "sweeps_detected":     setup.get("sweeps_detected", False),
            }
            try:
                send_elite_setup_alert(
                    pair=pair,
                    signal=signal,
                    entry_price=setup.get("entry_price"),
                    stop_loss=setup.get("stop_loss"),
                    take_profit=setup.get("take_profit"),
                    probability_score=prob,
                    confidence=prob,
                    rr_ratio=rr,
                    session=setup.get("session", "LIVE"),
                    timeframe=setup.get("timeframe", "H1"),
                    analysis_notes=setup.get("analysis_notes", ""),
                    smart_money=smart_money,
                )
            except Exception as tel_err:
                print(f"[execute_trade] Telegram error (non-fatal): {tel_err}")

        return result

    except Exception as e:
        elapsed = time.time() - start_time
        error_metrics.record_error("execute_trade", e)
        crew_logger.log_error(
            error_type="execution_error",
            agent_name="execution_engine",
            error_message=str(e),
        )
        print(f"[execute_trade] Error: {e}")
        return {"status": "REJECTED", "reason": f"Execution error: {e}"}
