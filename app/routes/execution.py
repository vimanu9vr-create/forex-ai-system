from fastapi import APIRouter

from app.agents.execution_agent import (
    ExecutionAgent
)
router = APIRouter()
agent = ExecutionAgent()

@router.post("/execute-trade")
def execute_trade(symbol: str, entry_price: float, exit_price: float, position_size: float):

    sample_trade = {
        "symbol": symbol,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "position_size": position_size
    }
    result = agent.execute_trade(symbol, entry_price, exit_price, position_size, sample_trade)
    return result
