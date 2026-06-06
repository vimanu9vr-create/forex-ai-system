from fastapi import APIRouter

from app.smart_money.bias import compute_market_bias

router = APIRouter()


@router.get("/bias")
def bias(pair: str = "EURUSD", interval: str = "1h"):
    """Real market bias for a pair from smart-money structure (BOS + CHoCH)."""
    return {"bias": compute_market_bias(pair, interval)}
