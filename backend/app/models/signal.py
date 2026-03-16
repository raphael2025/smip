from sqlalchemy import Column, BigInteger, String, Numeric
from sqlalchemy.dialects.postgresql import TIMESTAMP, JSONB
from app.database import Base


class Signal(Base):
    __tablename__ = "signals"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(32), nullable=False)
    signal_type = Column(String(10), nullable=False)
    confidence = Column(Numeric(4, 3), nullable=False)
    participants = Column(JSONB)
    avg_entry_price = Column(Numeric(20, 8))
    total_size = Column(Numeric(20, 8))
    created_at = Column(TIMESTAMP(timezone=True))
    expired_at = Column(TIMESTAMP(timezone=True))
