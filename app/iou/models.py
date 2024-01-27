from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import func
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import text

from app.core.db.session import Base

class EntryModel(Base):
    __tablename__ = 'entries'

    id = Column(Integer, primary_key=True, index=True)
    datetime = Column(DateTime, default=func.now(), server_default=text('CURRENT_TIMESTAMP'))
    conversation_id = Column(Integer)
    sender = Column(String)
    recipient = Column(String)
    amount = Column(Float)
    description = Column(String, nullable=True)
    deleted = Column(Boolean, default=False)
