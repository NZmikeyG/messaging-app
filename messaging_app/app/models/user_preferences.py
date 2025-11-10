from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class UserPreferences(Base):
    """User settings and preferences."""
    
    __tablename__ = "user_preferences"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    theme = Column(String(50), default="light")  # light, dark, auto
    notifications_enabled = Column(Boolean, default=True)
    email_notifications = Column(Boolean, default=True)
    notification_settings = Column(JSON, default={})  # Custom per-type settings
    privacy_level = Column(String(50), default="public")  # public, friends, private
    show_online_status = Column(Boolean, default=True)
    allow_dm_from = Column(String(50), default="anyone")  # anyone, friends, nobody
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User")
