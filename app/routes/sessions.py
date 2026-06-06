from fastapi import APIRouter

from app.smart_money.sessions import (
    detect_session
)
router = APIRouter()
@router.get("/sessions")
def sessions_analysis():

    result = detect_session()

    return result