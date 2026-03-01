from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.models.domain import User

router = APIRouter(tags=["Users"])


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "name": current_user.name,
            "google_id": current_user.google_id,
            "role": current_user.role,
            "created_at": current_user.created_at
        },
        "organisation": {
            "id": str(current_user.organisation.id),
            "name": current_user.organisation.name,
            "slug": current_user.organisation.slug,
            "created_at": current_user.organisation.created_at
        }
    }