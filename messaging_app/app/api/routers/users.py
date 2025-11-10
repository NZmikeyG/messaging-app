from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.api.schemas.user import UserPublic, UserProfileUpdate
from app.services.cache_service import cache_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/profile/{user_id}", response_model=UserPublic)
async def get_user_profile(
    user_id: str,
    db: Session = Depends(get_db),
):
    """Get user profile."""
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    # Try cache
    cache_key = f"user:{user_id}:profile"
    cached = await cache_service.get(cache_key)
    if cached:
        return cached
    
    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
        "status": user.status,
        "created_at": user.created_at,
    }
    
    # Cache result
    await cache_service.set(cache_key, result, ttl=300)
    
    return result


@router.put("/profile", response_model=UserPublic)
async def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user profile."""
    logger.info(f"Updating profile for user {current_user.id}")
    
    if profile_update.avatar_url is not None:
        current_user.avatar_url = profile_update.avatar_url
    if profile_update.bio is not None:
        current_user.bio = profile_update.bio
    if profile_update.status is not None:
        current_user.status = profile_update.status
    
    db.commit()
    db.refresh(current_user)
    
    # Invalidate cache
    await cache_service.invalidate_user_cache(str(current_user.id))
    
    logger.info(f"Profile updated for user {current_user.id}")
    
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "avatar_url": current_user.avatar_url,
        "bio": current_user.bio,
        "status": current_user.status,
        "created_at": current_user.created_at,
    }
