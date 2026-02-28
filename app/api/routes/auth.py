from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.api.dependencies import get_db
from app.core.security import verify_google_token, generate_access_token
from app.models.domain import User, Organisation

router = APIRouter(prefix="/auth", tags=["Authentication"])

class GoogleAuthRequest(BaseModel):
    token: str


@router.post("/google")
async def authenticate_google(request: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    google_data = await verify_google_token(request.token)
    if not google_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or Expired Google Token"
        )
    
    result = await db.execute(select(User).where(User.email == google_data["email"]))
    user = result.scalars().first()

    if not user:
        new_org = Organisation(
            name=f"{google_data['name']}'s Workspace",
            slug=f"{google_data['email'].split('@')[0]}-workspace"
        )
        db.add(new_org)
        await db.flush()

        user = User(
            email=google_data["email"],
            name=google_data["name"],
            google_id=google_data["google_id"],
            organisation_id=new_org.id,
            role="admin"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    access_token = generate_access_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "organisation_id": str(user.organisation_id),
            "role": user.role
        }
    }