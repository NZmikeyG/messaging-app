from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.utils.sanitizer import sanitizer


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    
    @field_validator('content')
    @classmethod
    def sanitize_content(cls, v):
        return sanitizer.sanitize_text(v)


class MessageUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    
    @field_validator('content')
    @classmethod
    def sanitize_content(cls, v):
        return sanitizer.sanitize_text(v)


class MessageUser(BaseModel):
    id: str
    username: str
    email: str

    @field_validator('id', mode='before')
    @classmethod
    def convert_id_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


class MessagePublic(BaseModel):
    id: str
    content: str
    channel_id: str
    user_id: str
    user: MessageUser
    created_at: datetime
    updated_at: datetime
    is_edited: bool
    is_deleted: bool

    @field_validator('id', 'channel_id', 'user_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


class MessageSender(BaseModel):
    id: str
    username: str
    email: str

    @field_validator('id', mode='before')
    @classmethod
    def convert_id_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


class FilePublic(BaseModel):
    id: str
    channel_id: str
    sender_id: str
    sender: MessageSender
    filename: str
    file_type: str
    file_size: int
    created_at: datetime

    @field_validator('id', 'channel_id', 'sender_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True
