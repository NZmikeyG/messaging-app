from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base


class DirectMessage(Base):
    __tablename__ = "direct_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    sender_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    receiver_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_edited = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)

    sender = relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], backref="received_messages")

    __table_args__ = (
        CheckConstraint('sender_id != receiver_id', name='different_users'),
    )
