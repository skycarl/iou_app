from typing import Optional
from pydantic import BaseModel


class EntryBase(BaseModel):
    conversation_id: int
    sender: str
    recipient: str
    amount: float
    description: Optional[str] = None


class EntryCreate(EntryBase):
    pass


class Entry(EntryBase):
    id: int

    class Config:
        orm_mode = True


class IOUStatus(BaseModel):
    user1: str
    user2: str
    amount: float

    class Config:
        orm_mode = True
