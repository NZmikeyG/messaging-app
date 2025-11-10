from datetime import datetime, timedelta
from jose import JWTError, jwt
from pydantic import BaseModel
import os

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))


class TokenData(BaseModel):
    user_id: str
    email: str


def create_access_token(user_id: str, email: str) -> str:
    """Create a JWT access token."""
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    
    to_encode = {
        "user_id": user_id,
        "email": email,
        "exp": expire
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> TokenData:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        email = payload.get("email")
        
        if user_id is None or email is None:
            raise JWTError("Invalid token")
        
        return TokenData(user_id=user_id, email=email)
    except JWTError:
        raise JWTError("Invalid or expired token")
