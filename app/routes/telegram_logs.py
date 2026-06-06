from fastapi import APIRouter
from sqlalchemy import desc

from app.database import SessionLocal
from app.models.trade_model import Trade

router = APIRouter()


@router.get('/telegram-logs')
def telegram_logs(limit: int = 50):
    db = SessionLocal()
    try:
        rows = (
            db.query(Trade)
            .order_by(desc(Trade.opened_at))
            .limit(max(1, min(limit, 200)))
            .all()
        )
    finally:
        db.close()

    logs = []
    for trade in rows:
        stamp = trade.opened_at.isoformat() if trade.opened_at else 'N/A'
        side = trade.signal or trade.direction or 'N/A'
        logs.append(
            f"[{stamp}] {trade.pair} {side} | status={trade.status} | "
            f"entry={trade.entry_price} | sl={trade.stop_loss} | "
            f"tp={trade.take_profit} | pnl={trade.pnl}"
        )

    return {"logs": logs}
