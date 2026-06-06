from fastapi import APIRouter

from sqlalchemy import func

from app.database import SessionLocal
from app.models.trade_model import Trade

router = APIRouter()
@router.get("/analytics")

def analytics ():
    db = SessionLocal()

    total_trades = db.query(Trade).count()
    long_trades = db.query(Trade).filter(Trade.direction == "long").count()
    short_trades = db.query(Trade).filter(Trade.direction == "short").count()
    open_trades = db.query(Trade).filter(Trade.status == "open").count()
    closed_trades = db.query(Trade).filter(Trade.status == "closed").count()

    avg_probability =(
        db.query(
            func.avg(
                Trade.probability_score
            )
                ).scalar())

    pair_stats = (
        db.query(
            Trade.pair,
            func.count(Trade.id)
        )
        .group_by(
            Trade.pair
        )
        .all()
    )

    db.close()

    return {
        "total_trades": total_trades,
        "buy_trades": long_trades,
        "sell_trades": short_trades,
        "open_trades": open_trades,
        "closed_trades": closed_trades,
        "avg_probability": round(float(avg_probability or 0), 2),
        "pair_stats": [
            {"pair": pair, "trades": count}
            for pair, count in pair_stats
        ]
    }
