from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from app.database import get_db
from app.models.user import User
from app.utils.security import hash_password, verify_password
from app.utils.jwt_utils import create_access_token
from app.dependencies import get_current_user
import logging


logger = logging.getLogger(__name__)

# CREATE ROUTER FIRST - BEFORE USING IT
router = APIRouter()


# ============ SCHEMAS ============

class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    username: str

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserPublic


# ============ ENDPOINTS ============

@router.post("/register", response_model=UserPublic, status_code=201)
def register(user: UserRegister, db: Session = Depends(get_db)):
    """Register a new user."""
    logger.info(f"Registration attempt for email: {user.email}")
    
    if db.query(User).filter(User.email == user.email).first():
        logger.warning(f"Registration failed - email already registered: {user.email}")
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed = hash_password(user.password[:72])
    new_user = User(email=user.email, username=user.username, password_hash=hashed)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"User registered successfully: {user.email}")
    return {
        "id": str(new_user.id),
        "email": new_user.email,
        "username": new_user.username
    }


@router.post("/login", response_model=TokenResponse)
def login(user: UserLogin, db: Session = Depends(get_db)):
    """Login user and return access token."""
    logger.info(f"Login attempt for email: {user.email}")
    
    db_user = db.query(User).filter(User.email == user.email).first()
    
    if not db_user:
        logger.warning(f"Login failed - user not found: {user.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(user.password[:72], db_user.password_hash):  # CHANGED: hashed_password → password_hash
        logger.warning(f"Login failed - invalid password for: {user.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token(data={"sub": str(db_user.id)})
    
    logger.info(f"User logged in successfully: {user.email}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(db_user.id),
            "email": db_user.email,
            "username": db_user.username
        }
    }


@router.get("/me", response_model=UserPublic)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    logger.info(f"Fetching user info for: {current_user.email}")
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "username": current_user.username
    }
