from sqlalchemy import Column, String, Numeric, Integer, Boolean, Interval
from sqlalchemy.dialects.postgresql import TIMESTAMP
from app.database import Base


class Trader(Base):
    __tablename__ = "traders"

    wallet_address = Column(String(66), primary_key=True)
    total_pnl = Column(Numeric(20, 8), default=0)
    win_rate = Column(Numeric(5, 2), default=0)
    trade_count = Column(Integer, default=0)
    max_drawdown = Column(Numeric(5, 2), default=0)
    avg_hold_time = Column(Interval)
    profit_factor = Column(Numeric(10, 4), default=0)
    score = Column(Numeric(10, 4), default=0)
    last_trade_time = Column(TIMESTAMP(timezone=True))
    is_smart_money = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True))
