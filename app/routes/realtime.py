import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import DASHBOARD_PAIRS
from app.services.signal_service import get_live_signals

router = APIRouter()

# Push interval — no point pushing faster than the candle interval.
# Candles are 5-min; 60s keeps the UI fresh without burning API credits.
WS_PUSH_INTERVAL = 60  # seconds


@router.websocket("/ws/signals")
async def signals_socket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Push the SAME all-pairs dashboard view as the HTTP /signals route (show_all over
            # DASHBOARD_PAIRS) — otherwise the WS would override it with the disciplined 2-pair set.
            await websocket.send_json({
                "type": "signals",
                "signals": get_live_signals(pairs=DASHBOARD_PAIRS, show_all=True),
            })
            await asyncio.sleep(WS_PUSH_INTERVAL)
    except WebSocketDisconnect:
        return
