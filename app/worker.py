import asyncio
import uuid
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import engine
from app.models.domain import CreditTransaction
from app.core.config import settings


async def summarise_text(ctx, job_id: str, org_id: uuid.UUID, user_id: uuid.UUID, text: str):
    try:
        await asyncio.sleep(10)

        if "crash" in text.lower():
            raise Exception("Simulated background worker failure")
        
        word_count = len(text.split())
        return f"Summary complete. Reduced {word_count} words to 3 bullet points."
    
    except Exception as e:
        async with AsyncSession(engine) as db:
            refund_transaction = CreditTransaction(
                organisation_id=org_id,
                user_id=user_id,
                amount=10,
                reason=f"Refund for failed summarisation job: {job_id}"
            )
            db.add(refund_transaction)
            await db.commit()
        
        raise e


class WorkerSettings:
    functions = [summarise_text]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)