from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class UserRole(Base):
    """Define user roles and permissions."""
    
    __tablename__ = "user_roles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    permissions = Column(ARRAY(String), default=[])  # List of permission strings
    is_system_role = Column(Boolean, default=False)  # System roles can't be deleted
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user_role_assignments = relationship("UserRoleAssignment", back_populates="role")


class UserRoleAssignment(Base):
    """Assign roles to users."""
    
    __tablename__ = "user_role_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("user_roles.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")
    role = relationship("UserRole", back_populates="user_role_assignments")
