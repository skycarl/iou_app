from typing import Optional
from pydantic import BaseModel, validator


class EntryBase(BaseModel):
    conversation_id: int
    sender: str
    recipient: str
    amount: float
    description: Optional[str] = None

    @validator('amount')
    def validate_amount(cls, amount):
        """Validate that amount is positive"""

        if amount <= 0:
            raise ValueError('Amount must be positive')
        return amount

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
