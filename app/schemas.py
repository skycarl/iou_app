from typing import Optional, Dict, List
from pydantic import BaseModel


class EntryBase(BaseModel):
    sender: str
    recipient: str
    amount: float
    description: Optional[str] = None


class EntryCreate(EntryBase):
    sender: str
    recipient: str
    amount: float
    description: Optional[str] = None


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
