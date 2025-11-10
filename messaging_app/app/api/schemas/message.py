from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class MessageUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


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
