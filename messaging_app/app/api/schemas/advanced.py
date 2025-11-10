from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID


class TwoFactorSetup(BaseModel):
    secret_key: str
    qr_code_url: Optional[str] = None


class TwoFactorVerify(BaseModel):
    code: str


class EncryptedMessageCreate(BaseModel):
    message_id: str
    encrypted_content: str
    encryption_key_id: Optional[str] = None


class ScheduledMessageCreate(BaseModel):
    content: str
    channel_id: Optional[str] = None
    recipient_id: Optional[str] = None
    scheduled_for: datetime


class UserAnalyticsPublic(BaseModel):
    user_id: str
    total_messages_sent: int
    total_dms_sent: int
    channels_joined: int
    total_reactions: int
    avg_message_length: float
    last_active: datetime
    login_count: int

    @field_validator('user_id', mode='before')
    @classmethod
    def convert_id_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True
