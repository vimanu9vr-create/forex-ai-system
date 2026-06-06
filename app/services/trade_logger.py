from datetime import datetime
from app.database import SessionLocal
from app.models.trade_model import Trade


def save_trade(
    pair: str,
    signal: str,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    probability: float = 0,
    direction: str = None,
    status: str = "open",
):
    """Save an executed trade to the database."""
    session = SessionLocal()
    try:
        # Derive direction from signal if not provided
        if not direction:
            direction = "long" if str(signal).upper() in ("BUY", "LONG") else "short"

        new_trade = Trade(
            pair=str(pair).upper(),
            signal=str(signal).upper(),
            direction=direction,
            entry_price=float(entry_price or 0),
            stop_loss=float(stop_loss or 0),
            take_profit=float(take_profit or 0),
            pnl="0",
            status=status,
            opened_at=datetime.utcnow(),
            probability_score=float(probability or 0),
            sniper_signal="",
            killzone_active="",
            bias="",
            fvg_zones="",
            order_blocks="",
            sweeps="",
            choch="",
        )
        session.add(new_trade)
        session.commit()
        session.refresh(new_trade)
        print(f"✅ Trade saved to DB: {pair} {signal} @ {entry_price} (id={new_trade.id})")
        return new_trade.id
    except Exception as e:
        session.rollback()
        print(f"❌ Error saving trade to DB: {e}")
        return None
    finally:
        session.close()
