import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import field_validator
from pydantic import model_validator


class EntrySchema(BaseModel):
    conversation_id: str
    sender: str
    recipient: str
    amount: float
    description: Optional[str] = None
    timestamp: Optional[datetime.datetime] = None
    deleted: Optional[bool] = False

    @model_validator(mode='before')
    def cast_conversation_id(cls, data): #pylint: disable=no-self-argument
        """Cast conversation_id to string if it is an integer or float"""
        conversation_id = data.get('conversation_id')
        if isinstance(conversation_id, (int, float)):
            data['conversation_id'] = str(conversation_id)
        return data

    @field_validator('amount')
    def validate_amount(cls, amount): #pylint: disable=no-self-argument
        """Validate that amount is positive"""
        if amount <= 0:
            raise ValueError('Amount must be positive')
        return amount


class IOUStatus(BaseModel):
    owing_user: Optional[str]
    owed_user: Optional[str]
    amount: float


class SplitSchema(BaseModel):
    conversation_id: str
    payer: str
    amount: float
    participants: List[str]
    description: str


class User(BaseModel):
    username: str
    conversation_id: Optional[str] = None


class UserDB(BaseModel):
    users: List[User]


class UserUpdate(BaseModel):
    conversation_id: str
