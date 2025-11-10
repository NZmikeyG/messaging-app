from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class ChannelRole(Base):
    """Define roles within channels."""
    
    __tablename__ = "channel_roles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id"), nullable=False)
    name = Column(String(50), nullable=False)
    permissions = Column(ARRAY(String), default=[])  # channel_admin, manage_members, moderate, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    channel_role_assignments = relationship("ChannelRoleAssignment", back_populates="role")


class ChannelRoleAssignment(Base):
    """Assign channel roles to users."""
    
    __tablename__ = "channel_role_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("channel_roles.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")
    role = relationship("ChannelRole", back_populates="channel_role_assignments")
