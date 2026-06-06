from fastapi import APIRouter

from app.smart_money.liquidity_confirmation import (
    confirm_liquidity_grab
)
router = APIRouter()
@router.get("/liquidity-confirmation")
def analyze_liquidity_confirmation():

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
    result = confirm_liquidity_grab(
         sweeps,
         choch,
         killzone,
         multiple_timeframe
    )
    return result
