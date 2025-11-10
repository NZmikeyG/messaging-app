from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserPresenceCreate(BaseModel):
    status: str  # online, away, dnd, offline


class UserPresenceUpdate(BaseModel):
    is_online: Optional[bool] = None
    status: Optional[str] = None


class UserPresencePublic(BaseModel):
    user_id: str
    is_online: bool
    status: str
    last_seen: datetime

    @field_validator('user_id', mode='before')
    @classmethod
    def convert_id_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


class MessageReadReceiptCreate(BaseModel):
    message_id: str


class MessageReadReceiptPublic(BaseModel):
    message_id: str
    user_id: str
    read_at: datetime

    @field_validator('message_id', 'user_id', mode='before')
    @classmethod
    def convert_id_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True
