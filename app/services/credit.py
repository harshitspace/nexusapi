import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.domain import CreditTransaction

class InsufficientCreditsError(Exception):
    pass

async def deduct_credits(
        db: AsyncSession,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        amount: int,
        reason: str,
        idempotency_key: str | None
) -> CreditTransaction:
    
    if idempotency_key:
        idempotent_query = select(CreditTransaction).where(
            CreditTransaction.idempotency_key == idempotency_key,
            CreditTransaction.organisation_id == org_id
        )
        idempotent_result = await db.execute(idempotent_query)
        existing_transaction = idempotent_result.scalars().first()

        if existing_transaction:
            return existing_transaction
    
    balance_query = select(func.coalesce(func.sum(CreditTransaction.amount), 0)).where(
        CreditTransaction.organisation_id == org_id
    )
    balance_result = await db.execute(balance_query)
    current_balance = balance_result.scalars().first()

    if current_balance < amount:
        raise InsufficientCreditsError(
            f"Insufficient credits. You have {current_balance}, but tried to use {amount}."
        )
    
    new_transaction = CreditTransaction(
        organisation_id=org_id,
        user_id=user_id,
        amount=-amount,
        reason=reason,
        idempotency_key=idempotency_key
    )

    db.add(new_transaction)
    await db.commit()
    await db.refresh(new_transaction)

    return new_transaction