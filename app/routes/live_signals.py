from fastapi import APIRouter

from app.smart_money.live_signals import (
    generate_live_signal
)
router = APIRouter()
@router.get("/live-signals")
def analyze_live_signals():

    sniper_entry = {
        "sniper_entry": True,
        "direction": "long"
    }

    probability = {
        "score": 85
    }

    killzone = {
        "active": True 
    }
    result = generate_live_signal(
         sniper_entry,
         probability,
         killzone
    )
    return result