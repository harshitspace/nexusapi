from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.dependencies import get_db
from app.core.security import get_current_user
from app.models.domain import User, CreditTransaction
from app.schemas.product import AnalyseRequest
from app.services.credit import deduct_credits, InsufficientCreditsError

router = APIRouter(prefix="/api", tags=["Products"])


@router.post("/analyse")
async def analyse_text(
    payload: AnalyseRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db) 
):
    cost = 25

    try:
        transaction = await deduct_credits(
            db=db,
            org_id=current_user.organisation_id,
            user_id=current_user.id,
            amount=cost,
            reason="analyse_api",
            idempotency_key=idempotency_key
        )
    except InsufficientCreditsError as e:
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content={
                "error": "insufficient_credits",
                "balance": e.current_balance,
                "required": cost
            }
        )
    
    balance_query = select(func.coalesce(func.sum(CreditTransaction.amount), 0)).where(
        CreditTransaction.organisation_id == current_user.organisation_id
    )
    balance_result = await db.execute(balance_query)
    current_balance = balance_result.scalar()

    words = payload.text.split()
    word_count = len(words)
    unique_words = len(set(word.lower() for word in words))

    return {
        "result": f"Analysis complete. Word count: {word_count}. Unique words: {unique_words}.",
        "credits_remaining": current_balance
    }