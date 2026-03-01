from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.dependencies import get_db
from app.core.security import get_current_user
from app.models.domain import User, CreditTransaction
from app.schemas.credit import CreditDeductRequest, CreditBalanceResponse, CreditGrantRequest

router = APIRouter(prefix="/credits", tags=["Credits"])


@router.get("/balance", response_model=CreditBalanceResponse)
async def get_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(func.coalesce(func.sum(CreditTransaction.amount), 0)).where(
        CreditTransaction.organisation_id == current_user.organisation_id
    )
    result = await db.execute(query)
    current_balance = result.scalar()

    return CreditBalanceResponse(
        organisation_id=current_user.organisation_id,
        balance=current_balance
    )


@router.post("/deduct")
async def deduct_credits(
    request: CreditDeductRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    idempotent_query = select(CreditTransaction).where(
        CreditTransaction.idempotency_key == request.idempotency_key,
        CreditTransaction.organisation_id == current_user.organisation_id
    )
    idempotent_result = await db.execute(idempotent_query)
    existing_transactions = idempotent_result.scalars().first()

    if existing_transactions:
        return {
            "message": "Request already processesd",
            "transaction_id": str(existing_transactions.id),
            "status": "idempotent_success"
        }
    
    balance_query = select(func.coalesce(func.sum(CreditTransaction.amount), 0)).where(
        CreditTransaction.organisation_id == current_user.organisation_id
    )
    balance_result = await db.execute(balance_query)
    current_balance = balance_result.scalar()

    if current_balance < request.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient credits! You have {current_balance}, but tried to use {request.amount}."
        )
    
    new_transaction = CreditTransaction(
        organisation_id=current_user.organisation_id,
        user_id=current_user.id,
        amount=-request.amount,
        reason=request.reason,
        idempotency_key=request.idempotency_key
    )

    db.add(new_transaction)
    await db.commit()
    await db.refresh(new_transaction)

    return {
        "message": "Credits deducted successfully!",
        "transaction_id": str(new_transaction.id),
        "remaining_balance": current_balance - request.amount
    }


@router.post("/grant")
async def grant_credits(
    request: CreditGrantRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organisation admins can grant credits."
        )
    
    idempotent_query = select(CreditTransaction).where(
        CreditTransaction.idempotency_key == request.idempotency_key,
        CreditTransaction.organisation_id == current_user.organisation_id
    )
    idempotent_result = await db.execute(idempotent_query)
    existing_transaction = idempotent_result.scalars().first()

    if existing_transaction:
        return {
            "message": "Grant request already processed!",
            "transaction_id": str(existing_transaction.id),
            "status": "idempotent_success"
        }
    
    new_transaction = CreditTransaction(
        organisation_id=current_user.organisation_id,
        user_id=current_user.id,
        amount=request.amount,
        reason=request.reason,
        idempotency_key=request.idempotency_key
    )

    db.add(new_transaction)
    await db.commit()
    await db.refresh(new_transaction)
    
    return {
        "message": f"Successfully granted {request.amount} credits.",
        "transaction_id": str(new_transaction.id)
    }