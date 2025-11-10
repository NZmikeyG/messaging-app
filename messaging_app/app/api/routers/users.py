from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models.user import User
from app.dependencies import get_current_user
from pydantic import BaseModel


router = APIRouter()


class UserPublic(BaseModel):
    id: str
    email: str
    username: str

    class Config:
        from_attributes = True


@router.get("/search", response_model=list[UserPublic])
def search_users(
    query: str = Query(..., min_length=1, max_length=255),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search users by email or username."""
    # Search for users matching query
    users = db.query(User).filter(
        or_(
            User.email.ilike(f"%{query}%"),
            User.username.ilike(f"%{query}%")
        )
    ).all()
    
    return users


@router.get("/{user_id}", response_model=UserPublic)
def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific user by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.get("/", response_model=list[UserPublic])
def list_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all users (paginated)."""
    users = db.query(User).offset(skip).limit(limit).all()
    return users
