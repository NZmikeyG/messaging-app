from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base


class Calendar(Base):
    __tablename__ = "calendars"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), default="#3366cc")
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", backref="calendars", foreign_keys=[owner_id])
    events = relationship("CalendarEvent", backref="calendar", cascade="all, delete-orphan")
    members = relationship("CalendarMember", backref="calendar", cascade="all, delete-orphan")
    subscriptions = relationship("CalendarSubscription", backref="calendar", cascade="all, delete-orphan")


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    calendar_id = Column(UUID(as_uuid=True), ForeignKey('calendars.id'), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    location = Column(String(255), nullable=True)
    is_all_day = Column(Boolean, default=False)
    recurrence = Column(String(50), default="never")  # never, daily, weekly, monthly, yearly
    recurrence_end_date = Column(DateTime, nullable=True)
    google_event_id = Column(String(255), nullable=True)
    metadata_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", backref="created_events", foreign_keys=[created_by])


class CalendarMember(Base):
    __tablename__ = "calendar_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    calendar_id = Column(UUID(as_uuid=True), ForeignKey('calendars.id'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    permission = Column(String(50), default="view")  # view, edit, admin
    added_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="calendar_memberships")


class CalendarSubscription(Base):
    __tablename__ = "calendar_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    calendar_id = Column(UUID(as_uuid=True), ForeignKey('calendars.id'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    is_visible = Column(Boolean, default=True)
    subscribed_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="calendar_subscriptions")


class GoogleCalendarSync(Base):
    __tablename__ = "google_calendar_sync"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), unique=True, nullable=False)
    calendar_id = Column(UUID(as_uuid=True), ForeignKey('calendars.id'), nullable=True)
    google_calendar_id = Column(String(255), nullable=False)
    google_access_token = Column(Text, nullable=False)
    google_refresh_token = Column(Text, nullable=False)
    sync_enabled = Column(Boolean, default=True)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="google_sync", uselist=False)
