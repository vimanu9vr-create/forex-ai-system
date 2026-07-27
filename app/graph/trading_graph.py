"""
trading_graph — the deterministic trading pipeline re-expressed as a LangGraph StateGraph.

Same agents as agents/orchestrator.TradingOrchestrator (MarketAgent -> ReflectionAgent ->
AdaptiveAgent -> ExecutionAgent), but modelled as a typed state machine with EXPLICIT
CONDITIONAL ROUTING (short-circuit straight to END on: no data / no A+ setup / circuit-breaker
halt / sub-threshold confidence) and a CHECKPOINTER, so every run is inspectable and each step's
state is persisted per thread.

This is the deterministic control-flow counterpart to the CrewAI `trading_crew` (which does
LLM-collaborative desk analysis). Same underlying agents, two orchestration styles chosen per
the control-flow needs of each path. Entry point: run_trading_graph().

    scan ──(no setup)──────────────► END
      │
      └─► reflect ─► adapt ──(halt / low conf)──► END
                        │
                        └─► execute ─► END
"""

from typing import Optional, TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.agents.market_agent import MarketAgent
from app.agents.reflection_agent import ReflectionAgent
from app.agents.adaptive_agent import AdaptiveAgent
from app.agents.execution_agent import ExecutionAgent

# A+ thresholds after adaptive adjustment (mirrors TradingOrchestrator)
MIN_CONFIDENCE_TO_TRADE = 80
MIN_RR_TO_TRADE = 1.5

# Reuse the same agent instances the rest of the app uses.
_market = MarketAgent()
_reflection = ReflectionAgent()
_adaptive = AdaptiveAgent()
_execution = ExecutionAgent()


class TradingState(TypedDict, total=False):
    """The state threaded through the graph; each node returns a partial update."""
    pairs_scanned: int
    best_setup: Optional[dict]
    performance: dict
    adjusted_setup: Optional[dict]
    trade_result: dict
    decision: str          # set only when the pipeline resolves (terminal)
    reason: str


def _select_best_setup(results: list) -> Optional[dict]:
    """Highest-probability A+ setup across the scan (ported from TradingOrchestrator)."""
    best, best_prob = None, 0.0
    for item in results:
        fvg = item.get("fvg", {}).get("present", False)
        ob = item.get("order_blocks", {}).get("present", False)
        liq = item.get("liquidity", {}).get("liquidity_confirmation", {}).get("confirmed", False)
        sweeps = item.get("sweeps", {})
        swept = len(sweeps.get("buy_side", []) + sweeps.get("sell_side", [])) > 0
        sm_count = sum([fvg, ob, liq, swept])
        kz = item.get("killzone", {})
        for setup in item.get("setups", []):
            prob = float(setup.get("probability_score") or setup.get("confidence") or 0)
            rr = float(setup.get("rr_ratio") or 0)
            if prob < MIN_CONFIDENCE_TO_TRADE or rr < MIN_RR_TO_TRADE or sm_count < 2:
                continue
            if prob > best_prob:
                best_prob = prob
                best = {
                    **setup,
                    "pair": item.get("pair"),
                    "probability_score": prob, "confidence": prob,
                    "fvg_present": fvg, "order_blocks_present": ob,
                    "liquidity_confirmed": liq, "sweeps_detected": swept,
                    "killzone_active": kz.get("active", False),
                    "session": kz.get("info", {}).get("killzone", "N/A"),
                    "smart_money_count": sm_count,
                }
    return best


# ── Nodes (each returns a partial TradingState) ──────────────────────────────
def scan_node(state: TradingState) -> dict:
    results = _market.analyze_market()
    if not results:
        return {"decision": "NO_TRADE", "reason": "Market scanner returned no data", "pairs_scanned": 0}
    best = _select_best_setup(results)
    if not best:
        return {"decision": "NO_TRADE", "reason": "No setup meets A+ criteria", "pairs_scanned": len(results)}
    return {"pairs_scanned": len(results), "best_setup": best}


def reflect_node(state: TradingState) -> dict:
    return {"performance": _reflection.analyze_performance()}


def adapt_node(state: TradingState) -> dict:
    perf = state.get("performance", {})
    halt, reason = _adaptive.should_halt_trading(perf)
    if halt:
        return {"decision": "HALTED", "reason": reason}
    adjusted = _adaptive.adjust_confidence(state["best_setup"], perf)
    conf = float(adjusted.get("confidence", 0) or 0)
    if conf < MIN_CONFIDENCE_TO_TRADE:
        return {"adjusted_setup": adjusted, "decision": "NO_TRADE",
                "reason": f"Confidence {conf:.0f}% below threshold after adaptive adjustment"}
    return {"adjusted_setup": adjusted}


def execute_node(state: TradingState) -> dict:
    result = _execution.execute_trade(state["adjusted_setup"])
    return {"trade_result": result, "decision": result.get("status", "UNKNOWN")}


# ── Conditional routing — a terminal `decision` short-circuits to END ────────
def _after_scan(state: TradingState) -> str:
    return "end" if state.get("decision") else "continue"


def _after_adapt(state: TradingState) -> str:
    return "end" if state.get("decision") else "continue"


def _build():
    g = StateGraph(TradingState)
    g.add_node("scan", scan_node)
    g.add_node("reflect", reflect_node)
    g.add_node("adapt", adapt_node)
    g.add_node("execute", execute_node)
    g.add_edge(START, "scan")
    g.add_conditional_edges("scan", _after_scan, {"continue": "reflect", "end": END})
    g.add_edge("reflect", "adapt")
    g.add_conditional_edges("adapt", _after_adapt, {"continue": "execute", "end": END})
    g.add_edge("execute", END)
    return g.compile(checkpointer=MemorySaver())


trading_graph = _build()


def run_trading_graph(thread_id: str = "default") -> dict:
    """Run the pipeline through the compiled graph; return the final state as a plain dict."""
    config = {"configurable": {"thread_id": thread_id}}
    final = dict(trading_graph.invoke({}, config=config))
    final.setdefault("decision", final.get("trade_result", {}).get("status", "UNKNOWN"))
    return final


def graph_structure() -> dict:
    """Graph topology, for a status endpoint / docs."""
    return {
        "engine": "LangGraph StateGraph",
        "nodes": ["scan", "reflect", "adapt", "execute"],
        "edges": [
            "START -> scan",
            "scan -> reflect  |  END (no data / no A+ setup)",
            "reflect -> adapt",
            "adapt -> execute  |  END (circuit-breaker halt / sub-threshold confidence)",
            "execute -> END",
        ],
        "checkpointer": "MemorySaver",
        "note": "Deterministic control-flow layer; complements the CrewAI trading_crew.",
    }
