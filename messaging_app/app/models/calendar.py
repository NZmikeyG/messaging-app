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


from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid
from app.database import Base


class CalendarTag(Base):
    __tablename__ = "calendar_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    calendar_id = Column(UUID(as_uuid=True), ForeignKey('calendars.id'), nullable=False)
    name = Column(String(50), nullable=False)
    color = Column(String(7), default="#808080")
    created_at = Column(DateTime, default=datetime.utcnow)

    calendar = relationship("Calendar", backref="tags")


class EventReminder(Base):
    __tablename__ = "event_reminders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey('calendar_events.id'), nullable=False)
    reminder_type = Column(String(50), default="email")  # email, push, in_app
    remind_at = Column(DateTime, nullable=False)
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("CalendarEvent", backref="reminders")


class EventInvite(Base):
    __tablename__ = "event_invites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey('calendar_events.id'), nullable=False)
    invitee_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    status = Column(String(50), default="pending")  # pending, accepted, declined, tentative
    response_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("CalendarEvent", backref="invites")
    invitee = relationship("User", backref="event_invites", foreign_keys=[invitee_id])


class RecurringEventRule(Base):
    __tablename__ = "recurring_event_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_event_id = Column(UUID(as_uuid=True), ForeignKey('calendar_events.id'), nullable=False)
    frequency = Column(String(50), nullable=False)  # daily, weekly, monthly, yearly
    interval = Column(Integer, default=1)
    days_of_week = Column(String(20), nullable=True)  # for weekly: 0-6 (Mon-Sun)
    end_date = Column(DateTime, nullable=True)
    max_occurrences = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    original_event = relationship("CalendarEvent", backref="recurrence_rule", uselist=False, foreign_keys=[original_event_id])


class EventNotification(Base):
    __tablename__ = "event_notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey('calendar_events.id'), nullable=False)
    notification_type = Column(String(50), nullable=False)  # event_created, event_updated, reminder, invite, invite_response
    message = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="calendar_notifications")
    event = relationship("CalendarEvent", backref="notifications")


class TeamCalendarView(Base):
    __tablename__ = "team_calendar_views"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(UUID(as_uuid=True), ForeignKey('channels.id'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    included_calendars = Column(JSON, default={})  # {calendar_id: {user_id: True/False, ...}}
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    channel = relationship("Channel", backref="calendar_views")
    creator = relationship("User", backref="created_team_calendar_views", foreign_keys=[created_by])
