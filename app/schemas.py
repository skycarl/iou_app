from typing import Optional, Dict, List
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


class IOUStatus(BaseModel):
    name: str
    amount: float

    class Config:
        orm_mode = True
