from fastapi import APIRouter

from app.smart_money.sniper_entry import sniper_entry

router = APIRouter()

@router.get("/sniper-entry")
def sniper():
    probability = {
        "score": 90,
        "reasons": [
            "Sweeps detected",
            "CHoCH detected",
            "Killzone active",
            "Multi-timeframe alignment",
            "FVG zones detected",
            "Order blocks detected",
            "High probability of successful trade setup"
        ]
    }

    liquidity_confirmation = {"liquidity_grab_confirmed": True}
    premium_discount = {"zone": "discount", "favorable": True}

    result = sniper_entry(
        probability,
        liquidity_confirmation,
        premium_discount
    )
    return result