from fastapi import APIRouter
from app.agents.orchestrator import TradingOrchestrator

router = APIRouter()
_orchestrator = TradingOrchestrator()


@router.get("/orchestrator")
def orchestrator_run():
    """
    Run the full agent pipeline:
    MarketScan → Reflection → AdaptiveAdjust → Execute
    Returns trade decision with full context.
    """
    return _orchestrator.run()


@router.get("/orchestrator/status")
def orchestrator_status():
    """
    Check system health without executing a trade.
    Returns performance metrics and whether trading is active.
    """
    return _orchestrator.get_status()
