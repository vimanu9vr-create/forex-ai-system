from fastapi import APIRouter

from app.smart_money.multi_timeframe import (
    analyze_multi_timeframe
)
router = APIRouter()    
@router.get("/multi-timeframe")
def multi_timeframe_analysis():

    bias: str = "bullish"
    setup:str = "buy"

    higher_timeframe_bias = bias

    lower_timeframe_setup = [
        {  
        "type": setup,
        "confidence": 85,
        "details": "Strong bullish engulfing pattern with high volume"
    }]

    result = analyze_multi_timeframe(
        higher_timeframe_bias,
        lower_timeframe_setup
    )
    return result