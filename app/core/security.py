import jwt
from datetime import datetime, timedelta, timezone
import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.api.dependencies import get_db
from app.models.domain import User

security = HTTPBearer()

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRES_MINUTES = 60 * 24 * 7


def generate_access_token(data: dict) -> str:
    to_encode = data.copy()

    expires_in = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRES_MINUTES)

    to_encode.update({"exp": expires_in})

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def verify_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])

        user_id: str = payload.get("sub")

        if user_id is None:
            return None
        
        return user_id
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def verify_google_token(token: str) -> dict | None:
    google_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"

    async with httpx.AsyncClient() as client:
        response = await client.get(google_url)

        if response.status_code != 200:
            return None
        
        token_data: dict = response.json()

        if token_data.get("aud") != settings.GOOGLE_CLIENT_ID:
            return None
        
        return {
            "google_id": token_data.get("sub"),
            "email": token_data.get("email"),
            "name": token_data.get("name")
        }


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: AsyncSession = Depends(get_db)
) -> User:
    
    token = credentials.credentials
    user_id = verify_access_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or Expired Access Token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user