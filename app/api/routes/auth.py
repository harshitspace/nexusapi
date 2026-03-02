from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import select
import httpx

from app.api.dependencies import get_db
from app.core.config import settings
from app.core.security import verify_google_token, generate_access_token
from app.models.domain import User, Organisation

router = APIRouter(tags=["Authentication"])

REDIRECT_URI = settings.GOOGLE_REDIRECT_URI


@router.get("/google")
async def login_google():
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"response_type=code&"
        f"client_id={settings.GOOGLE_CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"scope=openid%20email%20profile&"
        f"access_type=offline"
    )
    return RedirectResponse(url=url)


@router.get("/callback")
async def auth_callback(code: str, db: AsyncSession = Depends(get_db)):
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google authentication failed. Invalid authorization code."
            )
        
        token_data = response.json()
        id_token = token_data.get("id_token")

        google_data = await verify_google_token(id_token)
        if not google_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired Google ID Token."
            )
    
    email = google_data["email"]
    full_domain = email.split('@')[1]
    company_name = full_domain.split(".")[0].capitalize()

    result = await db.execute(select(User).options(joinedload(User.organisation)).where(User.email == email))
    user = result.scalars().first()

    if not user:
        org_result = await db.execute(select(Organisation).where(Organisation.slug == full_domain))
        org = org_result.scalars().first()

        if not org:
            org = Organisation(
                name=f"{company_name.capitalize()} Workspace",
                slug=full_domain
            )
            db.add(org)
            await db.flush()
            role = "admin"
        else:
            role = "member"
        
        user = User(
            email=email,
            name=google_data["name"],
            google_id=google_data["google_id"],
            organisation_id=org.id,
            role=role
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    access_token = generate_access_token(
        user_id=str(user.id),
        organisation_id=str(user.organisation.id),
        role=user.role
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "organisation_id": user.organisation_id,
            "organisation_name": user.organisation.name
        }
    }