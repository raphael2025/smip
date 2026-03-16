from sqlalchemy import Column, BigInteger, String, Numeric
from sqlalchemy.dialects.postgresql import TIMESTAMP
from app.database import Base


class MarketTicker(Base):
    __tablename__ = "market_tickers"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(32), nullable=False)
    price = Column(Numeric(20, 8), nullable=False)
    price_change_24h = Column(Numeric(10, 4))
    volume_24h = Column(Numeric(20, 2))
    high_24h = Column(Numeric(20, 8))
    low_24h = Column(Numeric(20, 8))
    source = Column(String(20), nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True))
