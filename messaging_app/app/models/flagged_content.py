from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class FlaggedContent(Base):
    """Track flagged messages for moderation."""
    
    __tablename__ = "flagged_content"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False)
    flagged_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reason = Column(String(255), nullable=False)  # spam, harassment, inappropriate, etc.
    description = Column(Text, nullable=True)
    status = Column(String(20), default="pending")  # pending, reviewed, resolved, dismissed
    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action_taken = Column(String(100), nullable=True)  # deleted, warned, suspended, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    
    message = relationship("Message")
    flagged_by = relationship("User", foreign_keys=[flagged_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
