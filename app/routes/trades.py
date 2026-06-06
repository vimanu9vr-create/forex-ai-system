from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import desc, func

from app.database import SessionLocal
from app.models.trade_model import Trade
from app.services.oanda_service import place_market_order, status as oanda_status

router = APIRouter()


class TradeExecutionRequest(BaseModel):
    pair: str
    signal: str
    entry: float = 0
    stop_loss: float = 0
    take_profit: float = 0
    probability: float = 0
    units: int = 1000


def serialize_trade(trade):
    return {
        "id": trade.id,
        "pair": trade.pair,
        "signal": trade.signal,
        "direction": trade.direction,
        "entry_price": trade.entry_price,
        "stop_loss": trade.stop_loss,
        "take_profit": trade.take_profit,
        "pnl": trade.pnl,
        "status": trade.status,
        "opened_at": trade.opened_at,
        "closed_at": trade.closed_at,
        "probability_score": trade.probability_score,
    }


@router.get("/oanda/status")
def get_oanda_status():
    return oanda_status()


@router.post("/trades/execute")
def execute_signal_trade(payload: TradeExecutionRequest):
    order_result = place_market_order(payload.dict(), payload.units)
    direction = "long" if payload.signal.upper() == "BUY" else "short"

    db = SessionLocal()
    trade = Trade(
        pair=payload.pair.upper(),
        signal=payload.signal.upper(),
        direction=direction,
        entry_price=payload.entry,
        stop_loss=payload.stop_loss,
        take_profit=payload.take_profit,
        pnl="0",
        status="open",
        opened_at=datetime.utcnow(),
        probability_score=payload.probability,
        sniper_signal=str(order_result),
        killzone_active="",
        bias="",
        fvg_zones="",
        order_blocks="",
        sweeps="",
        choch="",
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    result = serialize_trade(trade)
    db.close()

    return {
        "trade": result,
        "order": order_result,
    }


@router.get("/trade-history")
def trade_history(limit: int = 50):
    db = SessionLocal()
    trades = (
        db.query(Trade)
        .order_by(desc(Trade.opened_at))
        .limit(max(1, min(limit, 200)))
        .all()
    )
    result = [serialize_trade(trade) for trade in trades]
    db.close()

    return result


@router.get("/performance")
def performance():
    db = SessionLocal()
    total_trades = db.query(Trade).count()
    open_trades = db.query(Trade).filter(Trade.status == "open").count()
    closed_trades = db.query(Trade).filter(Trade.status == "closed").count()
    avg_probability = db.query(func.avg(Trade.probability_score)).scalar() or 0

    pair_stats = (
        db.query(Trade.pair, func.count(Trade.id))
        .group_by(Trade.pair)
        .all()
    )
    db.close()

    return {
        "total_trades": total_trades,
        "open_trades": open_trades,
        "closed_trades": closed_trades,
        "avg_probability": round(float(avg_probability), 2),
        "pair_stats": [
            {"pair": pair, "trades": count}
            for pair, count in pair_stats
        ],
    }
