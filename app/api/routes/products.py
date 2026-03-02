import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from arq import create_pool
from arq.connections import RedisSettings
from arq.jobs import Job

from app.api.dependencies import get_db
from app.api.middleware import check_rate_limit
from app.core.security import get_current_user
from app.core.config import settings
from app.models.domain import User, CreditTransaction
from app.schemas.product import AnalyseRequest, SummariseRequest
from app.services.credit import deduct_credits, InsufficientCreditsError

router = APIRouter(tags=["Products"])


@router.post("/analyse", dependencies=[Depends(check_rate_limit)])
async def analyse_text(
    payload: AnalyseRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db) 
):
    cost = 25

    try:
        await deduct_credits(
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


@router.post("/summarise", dependencies=[Depends(check_rate_limit)])
async def summarise_text_async(
    payload: SummariseRequest,
    idempotency_key: str | None =  Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    cost = 10

    try:
        await deduct_credits(
            db=db,
            org_id=current_user.organisation_id,
            user_id=current_user.id,
            amount=cost,
            reason="summarise_api_async",
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
    
    redis = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    job_id = str(uuid.uuid4())

    await redis.enqueue_job(
        'summarise_text',
        job_id=job_id,
        org_id=current_user.organisation_id,
        user_id=current_user.id,
        text=payload.text,
        _job_id=job_id
    )

    balance_query = select(func.coalesce(func.sum(CreditTransaction.amount), 0)).where(
        CreditTransaction.organisation_id == current_user.organisation_id
    )
    balance_result = await db.execute(balance_query)
    current_balance = balance_result.scalar()

    return {
        "job_id": job_id,
        "status": "pending",
        "credits_remaining": current_balance
    }


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    redis = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    job = Job(job_id, redis)
    job_info = await job.info()

    if not job_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    job_org_id = job_info.kwargs.get('org_id')

    if str(job_org_id) != str(current_user.organisation_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this job"
        )
    
    job_status = await job.status()

    if job_status.value == "complete":
        if job_info.success:
            return {
                "job_id": job_id,
                "status": "complete",
                "result": job_info.result
            }
        else:
            return {
                "job_id": job_id,
                "status": "failed",
                "error": "Background worker failed during processing. Credits have been refunded to your account."
            }
    
    return {
        "job_id": job_id,
        "status": job_status.value
    }