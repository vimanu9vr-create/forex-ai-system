from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Enum,   
)

from app.database import Base
class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    pair = Column(String, index=True)
    signal =Column(String)
    direction = Column(Enum("long", "short", name="trade_direction"))
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    pnl = Column(String)
    status = Column(Enum("open", "closed", name="trade_status"))
    opened_at = Column(DateTime)
    closed_at = Column(DateTime, nullable=True)
    probability_score = Column(Float)
    sniper_signal = Column(String)
    killzone_active = Column(String)
    bias = Column(String)
    fvg_zones = Column(String)
    order_blocks = Column(String)
    sweeps = Column(String)
    choch = Column(String)
    def __repr__(self):
        return f"<Trade(pair={self.pair}, direction={self.direction}, entry_price={self.entry_price}, status={self.status})>"