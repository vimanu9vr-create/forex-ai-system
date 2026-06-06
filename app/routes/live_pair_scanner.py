from fastapi import APIRouter

from app.smart_money.live_pair_scanner import (
    live_pair_scanner
)
router = APIRouter()
@router.get("/live-pair-scanner")
def live_pair_scanner():

    results = live_pair_scanner()

    return {
        "results": results
    }   