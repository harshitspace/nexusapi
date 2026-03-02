from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.dependencies import get_db
from app.core.security import get_current_user
from app.models.domain import User, CreditTransaction
from app.schemas.credit import CreditDeductRequest, CreditBalanceResponse, CreditGrantRequest
from app.services.credit import deduct_credits, InsufficientCreditsError

router = APIRouter(tags=["Credits"])


@router.get("/balance", response_model=CreditBalanceResponse)
async def get_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    balance_query = select(func.coalesce(func.sum(CreditTransaction.amount), 0)).where(
        CreditTransaction.organisation_id == current_user.organisation_id
    )
    balance_result = await db.execute(balance_query)
    current_balance = balance_result.scalar()

    transaction_query = select(CreditTransaction).where(
        CreditTransaction.organisation_id == current_user.organisation_id
    ).order_by(CreditTransaction.created_at.desc()).limit(10)
    transaction_result = await db.execute(transaction_query)
    recent_transactions = transaction_result.scalars().all()

    return CreditBalanceResponse(
        organisation_id=current_user.organisation_id,
        balance=current_balance,
        recent_transactions=recent_transactions
    )


@router.post("/deduct")
async def deduct_credits_route(
    request: CreditDeductRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        transaction = await deduct_credits(
            db=db,
            org_id=current_user.organisation_id,
            user_id=current_user.id,
            amount=request.amount,
            reason=request.reason,
            idempotency_key=request.idempotency_key
        )
        return {
            "message": "Credits deducted successfully!",
            "transaction_id": str(transaction.id)
        }
    except InsufficientCreditsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


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