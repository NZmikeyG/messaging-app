from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base

class AdminAction(Base):
    """Track admin actions for audit logs."""
    __tablename__ = "admin_actions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action_type = Column(String(50), nullable=False)  # delete_message, ban_user, delete_channel, etc
    target_type = Column(String(50), nullable=False)  # user, message, channel, etc
    target_id = Column(UUID(as_uuid=True), nullable=False)
    reason = Column(Text, nullable=True)
    details = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    admin = relationship("User", foreign_keys=[admin_id])


class UserSuspension(Base):
    """Track user suspensions/bans."""
    __tablename__ = "user_suspensions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    suspended_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=False)
    suspended_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    suspended_until = Column(DateTime, nullable=True)  # NULL = permanent
    is_active = Column(Boolean, default=True, nullable=False)
    
    user = relationship("User", foreign_keys=[user_id])
    moderator = relationship("User", foreign_keys=[suspended_by])


class UserRole(Base):
    """User roles (Admin, Moderator, Member)."""
    __tablename__ = "user_roles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    role = Column(String(20), nullable=False, default="member")  # admin, moderator, member
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    user = relationship("User", foreign_keys=[user_id])
    admin = relationship("User", foreign_keys=[assigned_by])


class ChannelRole(Base):
    """Channel-specific roles (Owner, Moderator, Member)."""
    __tablename__ = "channel_roles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = Column(String(20), nullable=False, default="member")  # owner, moderator, member
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    channel = relationship("Channel", foreign_keys=[channel_id])
    user = relationship("User", foreign_keys=[user_id])


class FlaggedContent(Base):
    """Track flagged/reported messages for moderation."""
    __tablename__ = "flagged_content"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False)
    reported_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reason = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="pending", nullable=False)  # pending, reviewed, resolved, dismissed
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    action_taken = Column(String(100), nullable=True)  # deleted, warned, suspended, none
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    message = relationship("Message", foreign_keys=[message_id])
    reporter = relationship("User", foreign_keys=[reported_by])
    moderator = relationship("User", foreign_keys=[reviewed_by])
