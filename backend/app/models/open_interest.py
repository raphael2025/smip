from sqlalchemy import Column, BigInteger, String, Numeric
from sqlalchemy.dialects.postgresql import TIMESTAMP
from app.database import Base


class OpenInterest(Base):
    __tablename__ = "open_interest"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(32), nullable=False)
    long_oi = Column(Numeric(20, 8), nullable=False)
    short_oi = Column(Numeric(20, 8), nullable=False)
    source = Column(String(20), nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
