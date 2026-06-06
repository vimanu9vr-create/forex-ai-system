import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

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
            # get_live_signals() returns cached data unless cache expired
            await websocket.send_json({
                "type": "signals",
                "signals": get_live_signals(),
            })
            await asyncio.sleep(WS_PUSH_INTERVAL)
    except WebSocketDisconnect:
        return
