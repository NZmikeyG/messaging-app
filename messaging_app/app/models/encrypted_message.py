from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class EncryptedMessage(Base):
    """Store end-to-end encrypted messages."""
    
    __tablename__ = "encrypted_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), unique=True, nullable=False)
    encrypted_content = Column(Text, nullable=False)  # AES-256 encrypted content
    encryption_key_id = Column(String(255), nullable=True)  # Key identifier for key rotation
    is_decrypted = Column(String(50), default="pending")  # pending, decrypted, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    
    message = relationship("Message")
