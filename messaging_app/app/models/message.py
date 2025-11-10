from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
    is_edited = Column(Boolean, default=False)
    
    # Self-referential relationship for threading - CORRECTED
    parent_id = Column(UUID(as_uuid=True), ForeignKey('messages.id'), nullable=True)
    replies = relationship(
        'Message',
        back_populates='parent',
        remote_side=[id],
        cascade='all, delete-orphan',
        single_parent=True  # CRITICAL: Added this line!
    )
    parent = relationship(
        'Message',
        remote_side=[parent_id],
        back_populates='replies'
    )
    
    # Reactions
    reactions = relationship("MessageReaction", back_populates="message", cascade='all, delete-orphan')
    
    user = relationship("User")
    channel = relationship("Channel")
