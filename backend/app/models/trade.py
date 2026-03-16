from sqlalchemy import Column, BigInteger, String, Numeric, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import TIMESTAMP
from app.database import Base


class Trade(Base):
    __tablename__ = "trades"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    wallet_address = Column(String(66), ForeignKey("traders.wallet_address", ondelete="CASCADE"), nullable=False)
    symbol = Column(String(32), nullable=False)
    side = Column(String(5), nullable=False)
    size = Column(Numeric(20, 8), nullable=False)
    entry_price = Column(Numeric(20, 8), nullable=False)
    exit_price = Column(Numeric(20, 8))
    pnl = Column(Numeric(20, 8))
    open_time = Column(TIMESTAMP(timezone=True), nullable=False)
    close_time = Column(TIMESTAMP(timezone=True))
    is_closed = Column(Boolean, default=False)
    leverage = Column(Numeric(5, 2))
    source = Column(String(20), nullable=False)
