"""LangGraph trading-pipeline routes — deterministic StateGraph orchestration."""

from fastapi import APIRouter

from app.graph.trading_graph import run_trading_graph, graph_structure

router = APIRouter()


@router.get("/graph/run")
def graph_run(thread_id: str = "default"):
    """Run the trading pipeline as a LangGraph StateGraph
    (scan -> reflect -> adapt -> execute, with conditional short-circuits + checkpointing).
    Deterministic control-flow counterpart to the CrewAI /crew-analysis."""
    return run_trading_graph(thread_id=thread_id)


@router.get("/graph/structure")
def graph_struct():
    """Graph topology (nodes / conditional edges / checkpointer)."""
    return graph_structure()
