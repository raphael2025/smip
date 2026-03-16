from sqlalchemy import Column, BigInteger, String
from sqlalchemy.dialects.postgresql import TIMESTAMP, JSONB
from app.database import Base


class OrderbookSnapshot(Base):
    __tablename__ = "orderbook_snapshots"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(32), nullable=False)
    bids = Column(JSONB, nullable=False)
    asks = Column(JSONB, nullable=False)
    source = Column(String(20), nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
