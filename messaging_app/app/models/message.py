from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
    
    parent_id = Column(UUID(as_uuid=True), ForeignKey('messages.id'), nullable=True)
    replies = relationship('Message', back_populates='parent', remote_side=[id])
    parent = relationship('Message', remote_side=[id], back_populates='replies')
    
    reactions = relationship("MessageReaction", back_populates="message")
    
    user = relationship("User")
    channel = relationship("Channel")
