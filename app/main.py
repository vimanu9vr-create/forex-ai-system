from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware


from app.routes.market import (
    router as market_router
)

from app.routes.structure import (
    router as structure_router
)

from app.routes.liquidity import (
    router as liquidity_router
)

from app.routes.sweeps import (
    router as sweeps_router
)

from app.routes.bias import (
    router as bias_router
)

from app.routes.bos import (
    router as bos_router
)

from app.routes.choch import (
    router as choch_router
)

from app.routes.fvg import (
    router as fvg_router
)

from app.routes.entry_model import (
    router as entry_model_router
)

from app.routes.order_blocks import (
    router as order_blocks_router
)

from app.routes.premium_discount import (
    router as premium_discount_router
)
from app.routes.setups import (
    router as setups_router
)
from app.routes.agents import (
    router as agent_router
)

from app.routes.memory import (
    router as memory_router
)

from app.routes.reflection import (
    router as reflection_router
)

from app.routes.execution import (
    router as execution_router    
)

from app.routes.orchestrator import (
    router as orchestrator_router
)

from app.routes.crew import(
    router as crew_router
)

from app.routes.multi_timeframe import(
    router as multi_timeframe_router
)
from app.routes.sessions import(
    router as sessions_router
)

from app.routes.killzones import(
    router as killzones_router  
)

from app.routes.liquidity_confirmation import (
    router as liquidity_confirmation_router
)

from app.routes.probability import (
    router as probability_router
)
from app.routes.sniper_entry import (
    router as sniper_entry_router
)   

from app.routes.live_signals import (
    router as live_signals_router
)   

from app.routes.pair_scanner import (
    router as pair_scanner_router
)

from app.routes.live_pair_scanner import (
    router as live_pair_scanner_router
)
from app.routes.telegram_alert import (
    router as telegram_alerts_router
)

from app.routes.analytics import (
    router as analytics_router
)

from app.routes.dashboard import(
    router as dashboard_router
)

from app.routes.scheduler import(
    router as scheduler_router
)
from app.routes.signals import(
    router as signals_router
)
from app.routes.realtime import(
    router as realtime_router
)
from app.routes.trades import(
    router as trades_router
)
from app.routes.auth import(
    router as auth_router
)
from app.routes.telegram_logs import (
    router as telegram_logs_router
)
from app.routes.ai_analysis import (
    router as ai_analysis_router
)
from app.routes.settings import (
    router as settings_router
)
from app.routes.cache import (
    router as cache_router
)
from app.services.signal_scheduler import start_signal_scheduler, stop_signal_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Auto-start the signal scheduler when the server boots.
    It runs in a background daemon thread — Telegram alerts fire automatically
    every 15 minutes regardless of whether the frontend is open.
    """
    print("[main] 🚀 Server starting — launching signal scheduler...")
    start_signal_scheduler()
    yield
    print("[main] 🛑 Server shutting down — stopping scheduler...")
    stop_signal_scheduler()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(market_router)
app.include_router(structure_router)
app.include_router(liquidity_router)
app.include_router(sweeps_router)
app.include_router(bias_router)
app.include_router(choch_router)
app.include_router(setups_router)
app.include_router(agent_router)
app.include_router(memory_router)
app.include_router(bos_router)
app.include_router(reflection_router)
app.include_router(execution_router)
app.include_router(orchestrator_router)
app.include_router(crew_router)
app.include_router(fvg_router)
app.include_router(entry_model_router)
app.include_router(order_blocks_router) 
app.include_router(premium_discount_router)
app.include_router(multi_timeframe_router)
app.include_router(sessions_router)
app.include_router(killzones_router)
app.include_router(liquidity_confirmation_router)
app.include_router(probability_router)
app.include_router(sniper_entry_router)
app.include_router(live_signals_router)
app.include_router(pair_scanner_router)
app.include_router(live_pair_scanner_router)
app.include_router(telegram_alerts_router)
app.include_router(analytics_router)
app.include_router(dashboard_router)
app.include_router(scheduler_router)
app.include_router(signals_router)
app.include_router(realtime_router)
app.include_router(trades_router)
app.include_router(auth_router)
app.include_router(telegram_logs_router)
app.include_router(ai_analysis_router)
app.include_router(settings_router)
app.include_router(cache_router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse("app/static/index.html")
