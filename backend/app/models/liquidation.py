from sqlalchemy import Column, BigInteger, String, Numeric
from sqlalchemy.dialects.postgresql import TIMESTAMP
from app.database import Base


class Liquidation(Base):
    __tablename__ = "liquidations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(32), nullable=False)
    side = Column(String(5), nullable=False)
    price = Column(Numeric(20, 8), nullable=False)
    qty = Column(Numeric(20, 8), nullable=False)
    usd_value = Column(Numeric(20, 2))
    source = Column(String(20), nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
