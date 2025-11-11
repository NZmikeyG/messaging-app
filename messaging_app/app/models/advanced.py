from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Integer, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base

class TwoFactorAuth(Base):
    """Track 2FA settings and secrets."""
    __tablename__ = "two_factor_auth"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    is_enabled = Column(Boolean, default=False, nullable=False)
    secret = Column(String(32), nullable=True)  # TOTP secret (base32 encoded)
    backup_codes = Column(String, nullable=True)  # JSON list of backup codes
    enabled_at = Column(DateTime, nullable=True)
    
    user = relationship("User", foreign_keys=[user_id])


class DeviceSession(Base):
    """Track user device sessions."""
    __tablename__ = "device_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    device_name = Column(String(255), nullable=False)
    device_type = Column(String(50), nullable=False)  # mobile, desktop, web
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    last_active = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    user = relationship("User", foreign_keys=[user_id])


class MessageEncryption(Base):
    """Track encrypted messages."""
    __tablename__ = "message_encryption"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False, unique=True)
    encrypted_content = Column(Text, nullable=False)
    encryption_key_id = Column(String(100), nullable=False)
    algorithm = Column(String(50), default="AES-256-GCM", nullable=False)
    iv = Column(String(100), nullable=False)  # Initialization vector
    tag = Column(String(100), nullable=False)  # Authentication tag
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    message = relationship("Message", foreign_keys=[message_id])


class UserActivity(Base):
    """Track user activity for analytics."""
    __tablename__ = "user_activity"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)  # sent_message, created_channel, joined_channel, etc
    target_type = Column(String(50), nullable=False)  # message, channel, user, etc
    target_id = Column(UUID(as_uuid=True), nullable=True)
    metadata = Column(JSON, nullable=True)  # Additional context
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    user = relationship("User", foreign_keys=[user_id])


class SecurityAuditLog(Base):
    """Track security-related events."""
    __tablename__ = "security_audit_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_type = Column(String(100), nullable=False)  # login, failed_login, password_change, 2fa_enabled, etc
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False)  # success, failure
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    user = relationship("User", foreign_keys=[user_id])


class SearchIndex(Base):
    """Full-text search index for messages and channels."""
    __tablename__ = "search_index"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    indexed_type = Column(String(50), nullable=False)  # message, channel
    indexed_id = Column(UUID(as_uuid=True), nullable=False)
    content = Column(Text, nullable=False)
    keywords = Column(String, nullable=True)  # Space-separated keywords
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
