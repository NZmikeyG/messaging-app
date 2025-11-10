from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class Notification(Base):
    """User notifications for messages, mentions, and events."""
    
    __tablename__ = "notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # message, mention, block, channel_invite
    title = Column(String(255), nullable=False)
    message = Column(String(500), nullable=False)
    related_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    related_message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)
    related_channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id"), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    user = relationship("User", foreign_keys=[user_id])
