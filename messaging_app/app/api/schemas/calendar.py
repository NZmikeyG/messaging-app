from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class CalendarEventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    start_time: datetime
    end_time: datetime
    location: Optional[str] = Field(None, max_length=255)
    is_all_day: bool = False


class CalendarEventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=255)
    is_all_day: Optional[bool] = None


class CalendarEventPublic(BaseModel):
    id: str
    user_id: str
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    location: Optional[str]
    is_all_day: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CalendarSettingsPublic(BaseModel):
    is_public: bool

    model_config = ConfigDict(from_attributes=True)


class GoogleCalendarSync(BaseModel):
    authorization_code: str
