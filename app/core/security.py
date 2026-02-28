import jwt
from datetime import datetime, timedelta, timezone
import httpx

from app.core.config import settings

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