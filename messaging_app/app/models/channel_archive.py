from sqlalchemy import Column, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class ChannelArchive(Base):
    """Track archived channels."""
    
    __tablename__ = "channel_archives"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id"), unique=True, nullable=False)
    archived_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_archived = Column(Boolean, default=True)
    archived_at = Column(DateTime, default=datetime.utcnow)
    
    channel = relationship("Channel")
    archived_by = relationship("User")
