from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class TwoFactorAuth(Base):
    """Store 2FA settings for users."""
    
    __tablename__ = "two_factor_auth"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    is_enabled = Column(Boolean, default=False)
    secret_key = Column(String(255), nullable=True)  # TOTP secret
    backup_codes = Column(String(1000), nullable=True)  # Comma-separated backup codes
    created_at = Column(DateTime, default=datetime.utcnow)
    last_verified = Column(DateTime, nullable=True)
    
    user = relationship("User")
