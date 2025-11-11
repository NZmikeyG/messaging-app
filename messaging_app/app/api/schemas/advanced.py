from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

class TwoFactorSetupResponse(BaseModel):
    secret: str
    qr_code: str
    backup_codes: List[str]

class TwoFactorVerifyRequest(BaseModel):
    code: str

class TwoFactorDisableRequest(BaseModel):
    password: str

class DeviceSessionResponse(BaseModel):
    id: UUID
    device_name: str
    device_type: str
    ip_address: Optional[str]
    last_active: datetime
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserActivityResponse(BaseModel):
    id: UUID
    user_id: UUID
    action: str
    target_type: str
    target_id: Optional[UUID]
    metadata_payload: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True

class SecurityAuditLogResponse(BaseModel):
    id: UUID
    user_id: UUID
    event_type: str
    ip_address: Optional[str]
    status: str
    reason: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class AdvancedSearchRequest(BaseModel):
    query: str
    search_type: str  # all, messages, channels
    filters: Optional[Dict[str, Any]] = None
    limit: int = 50
    offset: int = 0

class AdvancedSearchResult(BaseModel):
    type: str
    id: UUID
    title: str
    preview: str
    relevance_score: float
    created_at: datetime

class UserAnalyticsResponse(BaseModel):
    user_id: UUID
    total_messages_sent: int
    total_channels_joined: int
    average_messages_per_day: float
    most_active_channel: Optional[str]
    last_active: datetime
    devices_active: int
    
    class Config:
        from_attributes = True

class AdminAnalyticsDashboard(BaseModel):
    total_users_active_today: int
    total_messages_today: int
    average_response_time_ms: float
    channels_created_today: int
    security_events_today: int
    failed_logins_today: int
    two_fa_enabled_users: int
    peak_hour: int
    engagement_rate: float

