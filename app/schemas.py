from typing import Optional, Dict, List
from pydantic import BaseModel


class EntryBase(BaseModel):
    sender: str
    amount: float
    description: Optional[str] = None


class EntryCreate(EntryBase):
    sender: str
    amount: float
    description: Optional[str] = None


class Entry(EntryBase):
    id: int

    class Config:
        orm_mode = True


class IOUStatus(BaseModel):
    sender: str
    amount: float

    class Config:
        orm_mode = True
