from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ============ NOTIFICATIONS ============

class NotificationCreate(BaseModel):
    type: str
    title: str
    message: str
    related_user_id: Optional[str] = None
    related_message_id: Optional[str] = None
    related_channel_id: Optional[str] = None


class NotificationPublic(BaseModel):
    id: str
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime

    @field_validator('id', mode='before')
    @classmethod
    def convert_id_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


# ============ USER BLOCKING ============

class UserBlockCreate(BaseModel):
    blocked_id: str


class UserBlockPublic(BaseModel):
    blocked_id: str
    created_at: datetime


# ============ MESSAGE PINNING ============

class PinnedMessageCreate(BaseModel):
    message_id: str
    channel_id: str


class PinnedMessagePublic(BaseModel):
    id: str
    message_id: str
    channel_id: str
    pinned_by_id: str
    created_at: datetime


# ============ CHANNEL ARCHIVE ============

class ChannelArchiveCreate(BaseModel):
    channel_id: str


# ============ USER PREFERENCES ============

class UserPreferencesUpdate(BaseModel):
    theme: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    email_notifications: Optional[bool] = None
    privacy_level: Optional[str] = None
    show_online_status: Optional[bool] = None
    allow_dm_from: Optional[str] = None


class UserPreferencesPublic(BaseModel):
    theme: str
    notifications_enabled: bool
    email_notifications: bool
    privacy_level: str
    show_online_status: bool
    allow_dm_from: str

    class Config:
        from_attributes = True


# ============ API KEYS ============

class APIKeyCreate(BaseModel):
    name: str
    expires_at: Optional[datetime] = None


class APIKeyPublic(BaseModel):
    id: str
    name: str
    key: str  # Show only on creation
    is_active: bool
    last_used: Optional[datetime] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

    @field_validator('id', mode='before')
    @classmethod
    def convert_id_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True
