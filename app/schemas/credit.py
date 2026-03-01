from pydantic import BaseModel, Field
import uuid


class CreditDeductRequest(BaseModel):
    amount: int = Field(..., description="Must be a positive number of credits to deduct", gt=0)
    reason: str = Field(..., description="Why are these credits being used?")

    idempotency_key: str = Field(..., description="Unique key to prevent double-charging")


class CreditBalanceResponse(BaseModel):
    organisation_id: uuid.UUID
    balance: int


class CreditGrantRequest(BaseModel):
    amount: int = Field(..., description="Must be a positive number of credits to grant", gt=0)
    reason: str = Field(..., description="Why are these credits being granted?")
    idempotency_key: str = Field(..., description="Unique key to prevent double-granting")