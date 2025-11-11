from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class UserRoleCreate(BaseModel):
    user_id: UUID
    role: str  # admin, moderator, member

class UserRoleResponse(BaseModel):
    id: UUID
    user_id: UUID
    role: str
    assigned_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ChannelRoleCreate(BaseModel):
    user_id: UUID
    role: str  # owner, moderator, member

class ChannelRoleResponse(BaseModel):
    id: UUID
    user_id: UUID
    role: str
    assigned_at: datetime

    model_config = ConfigDict(from_attributes=True)

class FlagMessageRequest(BaseModel):
    reason: str
    description: Optional[str] = None

class FlaggedContentResponse(BaseModel):
    id: UUID
    message_id: UUID
    reported_by: UUID
    reason: str
    description: Optional[str]
    status: str
    reviewed_by: Optional[UUID]
    reviewed_at: Optional[datetime]
    action_taken: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ReviewFlagRequest(BaseModel):
    status: str  # reviewed, resolved, dismissed
    action_taken: Optional[str] = None

class SuspendUserRequest(BaseModel):
    reason: str
    suspended_until: Optional[datetime] = None  # NULL = permanent

class UserSuspensionResponse(BaseModel):
    id: UUID
    user_id: UUID
    reason: str
    suspended_at: datetime
    suspended_until: Optional[datetime]
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class AdminActionResponse(BaseModel):
    id: UUID
    admin_id: UUID
    action_type: str
    target_type: str
    target_id: UUID
    reason: Optional[str]
    details: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AdminDashboardStats(BaseModel):
    total_users: int
    total_channels: int
    total_messages: int
    total_flagged: int
    flagged_pending: int
    total_suspended: int
    admin_actions_today: int
    flagged_by_reason: dict
