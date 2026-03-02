import time
from fastapi import Request, HTTPException, Depends, status
from redis.asyncio import Redis

from app.core.config import settings
from app.core.security import get_current_user
from app.models.domain import User

redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

async def check_rate_limit(request: Request, current_user: User = Depends(get_current_user)):
    try:
        org_id = str(current_user.organisation_id)
        current_minute = int(time.time() // 60)
        key = f"rate_limit:{org_id}:{current_minute}"

        request_this_minute = await redis_client.incr(key)

        if request_this_minute == 1:
            await redis_client.expire(key, 60)
        
        if request_this_minute > 60:
            ttl = await redis_client.ttl(key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Maximum 60 requests per minute.",
                headers={
                    "Retry-After": str(ttl if ttl > 0 else 60)
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        print("Redis Rate Limiter Error: ", e)
        pass