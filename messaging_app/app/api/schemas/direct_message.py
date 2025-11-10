from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID


class DirectMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    receiver_id: str


class DirectMessageUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class DMUser(BaseModel):
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


class DirectMessagePublic(BaseModel):
    id: str
    content: str
    sender_id: str
    receiver_id: str
    sender: DMUser
    receiver: DMUser
    created_at: datetime
    updated_at: datetime
    is_edited: bool
    is_deleted: bool
    is_read: bool

    @field_validator('id', 'sender_id', 'receiver_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True
