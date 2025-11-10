from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from app.utils.jwt_utils import decode_access_token
from app.database import get_db
from app.models.user import User
from sqlalchemy.orm import Session


security = HTTPBearer()


def get_current_user(
    credentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user from JWT token."""
    token = credentials.credentials
    
    try:
        token_data = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user
