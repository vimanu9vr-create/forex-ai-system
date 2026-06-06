from fastapi import APIRouter

from app.smart_money.probability_engine import (
    calculate_probability
)
router = APIRouter()
@router.get("/probability")
def analyze_probability():

    sweeps ={
        "swept": True 
    }

    choch = {
        "choch": True 
    }

    killzone = {
        "active": True 
    }

    multiple_timeframe = {
        "valid": True 
    }
    fvg = {
        "present": True 
    }
    order_block = {
        "present": True 
    }
    
    result = calculate_probability(
         sweeps,
         choch,
         killzone,
         multiple_timeframe,
         fvg,
        order_block
    )
    return result