from fastapi import APIRouter

from app.smart_money.killzones import (
    detect_killzone
)
router = APIRouter()    
@router.get("/killzones")
def analyze_killzones():
    
    killzone = detect_killzone()

    return {
        "killzone": killzone
    }   