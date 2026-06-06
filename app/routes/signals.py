from fastapi import APIRouter

from app.services.signal_service import get_live_signals

router = APIRouter()


@router.get("/signals")
def get_signals():
    return get_live_signals()
