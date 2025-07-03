import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import computed_field
from pydantic import field_validator
from pydantic import model_validator

class AmountException(ValueError):
    pass

def validate_amount_str(amount: str) -> float:
    """Normalize and validate a user‑entered amount string."""
    if any(c.isalpha() for c in amount):
        raise AmountException(f'Amount "{amount}" contains invalid characters')
    cleaned = ''.join(c for c in amount if c.isdigit() or c in '.-')
    try:
        value = float(cleaned)
    except ValueError as e:
        raise AmountException(f'Unable to parse amount "{amount}"') from e
    if value <= 0:
        raise AmountException(f'Amount must be positive (got "{amount}")')
    return value

class EntrySchema(BaseModel):
    conversation_id: str
    sender: str
    recipient: str
    amount: float
    description: Optional[str] = None
    timestamp: Optional[datetime.datetime] = None
    deleted: Optional[bool] = False

    @model_validator(mode='before')
    def cast_conversation_id(cls, data):
        cid = data.get('conversation_id')
        if isinstance(cid, (int, float)):
            data['conversation_id'] = str(cid)
        return data

    @field_validator('amount')
    def positive_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v

class IOUMessage(BaseModel):
    conversation_id: int
    sender: str
    recipient: str
    amount: float
    description: Optional[str]

    @field_validator('sender', 'recipient')
    def strip_at(cls, v):
        return v.lstrip('@')

    @field_validator('amount', mode='before')
    def parse_amount(cls, v):
        if isinstance(v, str):
            return validate_amount_str(v)
        if isinstance(v, (int, float)):
            if v <= 0:
                raise AmountException(f'Amount must be positive (got "{v}")')
            return float(v)
        raise AmountException(f'Invalid amount type: {type(v)}')

    @computed_field
    def amount_str(self) -> str:
        return f"${self.amount:,.2f}"

class IOUQuery(BaseModel):
    conversation_id: int
    user1: str
    user2: str

    @field_validator('user1', 'user2')
    def strip_at(cls, v):
        return v.lstrip('@')

class IOUStatus(BaseModel):
    owing_user: Optional[str]
    owed_user: Optional[str]
    amount: float

    @field_validator('amount')
    def round_amount(cls, v):
        return round(v, 2)

class SplitSchema(BaseModel):
    conversation_id: str
    payer: str
    amount: float
    participants: List[str]
    description: str

    @field_validator('payer')
    def strip_at(cls, v):
        return v.lstrip('@')

    @field_validator('amount', mode='before')
    def parse_amount(cls, v):
        if isinstance(v, str):
            return validate_amount_str(v)
        if isinstance(v, (int, float)):
            if v <= 0:
                raise AmountException(f'Amount must be positive (got "{v}")')
            return float(v)
        raise AmountException(f'Invalid amount type: {type(v)}')

    @computed_field
    def amount_str(self) -> str:
        return f"${self.amount:,.2f}"

class SplitResponse(BaseModel):
    message: str
    amount: float
    split_per_user: float
    participants: List[str]

    @field_validator('amount', 'split_per_user')
    def round_amount(cls, v):
        return round(v, 2)

    @computed_field
    def amount_str(self) -> str:
        return f"${self.amount:,.2f}"

    @computed_field
    def split_per_user_str(self) -> str:
        return f"${self.split_per_user:,.2f}"

class TransactionEntry(BaseModel):
    conversation_id: str
    sender: str
    recipient: str
    amount: float
    description: Optional[str] = ''
    timestamp: Optional[str] = None

    @computed_field
    def amount_str(self) -> str:
        return f"${self.amount:,.2f}"

    @computed_field
    def formatted_date(self) -> str:
        if not self.timestamp:
            return ''
        try:
            dt = datetime.datetime.fromisoformat(self.timestamp)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            return self.timestamp

class User(BaseModel):
    username: str
    conversation_id: Optional[str] = None

class UserUpdate(BaseModel):
    conversation_id: str
