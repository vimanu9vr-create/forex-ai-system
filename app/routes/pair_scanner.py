from fastapi import APIRouter

from app.smart_money.pair_scanner import (
    scan_pairs
)
router = APIRouter()
@router.get("/pair-scanner")
def pair_scanner():

    results = scan_pairs()

    return {
        "results": results
    }