from sqlalchemy import Column, Integer, DateTime, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class UserAnalytics(Base):
    """Track user activity metrics."""
    
    __tablename__ = "user_analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    total_messages_sent = Column(Integer, default=0)
    total_dms_sent = Column(Integer, default=0)
    channels_joined = Column(Integer, default=0)
    total_reactions = Column(Integer, default=0)
    avg_message_length = Column(Float, default=0.0)
    last_active = Column(DateTime, default=datetime.utcnow)
    login_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User")
