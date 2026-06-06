from fastapi import APIRouter

from app.memory.trade_memory import (
    add_trade_to_history,
    get_trade_history

)
router = APIRouter()
@router.post("/add-trade")
def add_trade():

    sample_trade = {
        "symbol": "EUR/USD",
        "entry_price": 1.2345,
        "exit_price": 1.2350,
        "position_size": 1000,
        "profit_loss": 5.00,
        "timestamp": "2024-06-01T12:00:00Z"
    }
    
    result = add_trade_to_history(sample_trade)

    return result

@router.get("/trade-history")
def read_trade_history():
    return get_trade_history()