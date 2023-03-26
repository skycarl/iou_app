from sqlalchemy import Column, Integer, String, Float, DateTime, text, func
from .database import Base


class Entry(Base):
    __tablename__ = "entries"

    id = Column(Integer, primary_key=True, index=True)
    datetime = Column(DateTime, default=func.now(), server_default=text('CURRENT_TIMESTAMP'))
    name = Column(String)
    amount = Column(Float)
    description = Column(String, nullable=True)
