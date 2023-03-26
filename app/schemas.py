from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class EntryBase(BaseModel):
    name: str
    amount: float
    description: Optional[str] = None


class EntryCreate(EntryBase):
    name: str
    amount: float
    description: Optional[str] = None


class Entry(EntryBase):
    id: int

    class Config:
        orm_mode = True
