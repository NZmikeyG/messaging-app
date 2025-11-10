from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class UserRoleBase(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: List[str] = []


class UserRoleCreate(UserRoleBase):
    pass


class UserRolePublic(UserRoleBase):
    id: str
    is_system_role: bool
    created_at: datetime

    @field_validator('id', mode='before')
    @classmethod
    def convert_id_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


class ChannelRoleBase(BaseModel):
    name: str
    permissions: List[str] = []


class ChannelRoleCreate(ChannelRoleBase):
    channel_id: str


class ChannelRolePublic(ChannelRoleBase):
    id: str
    channel_id: str
    created_at: datetime

    @field_validator('id', 'channel_id', mode='before')
    @classmethod
    def convert_id_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


class FlaggedContentBase(BaseModel):
    message_id: str
    reason: str
    description: Optional[str] = None


class FlaggedContentCreate(FlaggedContentBase):
    pass


class FlaggedContentPublic(FlaggedContentBase):
    id: str
    flagged_by_id: str
    status: str
    reviewed_by_id: Optional[str] = None
    action_taken: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    @field_validator('id', 'message_id', 'flagged_by_id', 'reviewed_by_id', mode='before')
    @classmethod
    def convert_id_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True
