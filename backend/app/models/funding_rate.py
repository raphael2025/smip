from sqlalchemy import Column, BigInteger, String, Numeric
from sqlalchemy.dialects.postgresql import TIMESTAMP
from app.database import Base


class FundingRate(Base):
    __tablename__ = "funding_rates"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(32), nullable=False)
    rate = Column(Numeric(20, 10), nullable=False)
    source = Column(String(20), nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
