from pydantic import BaseModel, Field, ConfigDict
import uuid
from datetime import datetime
from typing import List, Optional


class CreditDeductRequest(BaseModel):
    amount: int = Field(..., description="Must be a positive number of credits to deduct", gt=0)
    reason: str = Field(..., description="Why are these credits being used?")
    idempotency_key: str = Field(..., description="Unique key to prevent double-charging")


class TransactionResponse(BaseModel):
    id: uuid.UUID
    amount: int
    reason: str
    idempotency_key: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreditBalanceResponse(BaseModel):
    organisation_id: uuid.UUID
    balance: int
    recent_transactions: List[TransactionResponse]


class CreditGrantRequest(BaseModel):
    amount: int = Field(..., description="Must be a positive number of credits to grant", gt=0)
    reason: str = Field(..., description="Why are these credits being granted?")
    idempotency_key: str = Field(..., description="Unique key to prevent double-granting")