from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserProfile(BaseModel):
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    status: Optional[str] = "Available"


class UserProfileUpdate(BaseModel):
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    status: Optional[str] = None


class UserPublic(BaseModel):
    id: str
    username: str
    email: EmailStr
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    status: Optional[str] = "Available"
    created_at: datetime

    @field_validator('id', mode='before')
    @classmethod
    def convert_id_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True
