from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID
from typing import List
import logging

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.user_role import UserRole, UserRoleAssignment
from app.models.channel_role import ChannelRole, ChannelRoleAssignment
from app.models.flagged_content import FlaggedContent
from app.models.message import Message
from app.models.channel import Channel
from app.api.schemas.role import (
    UserRoleCreate, UserRolePublic,
    ChannelRoleCreate, ChannelRolePublic,
    FlaggedContentCreate, FlaggedContentPublic
)
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)

router = APIRouter()

# ============ PERMISSION HELPERS ============

def check_admin(current_user: User, db: Session):
    """Check if user is admin."""
    admin_role = db.query(UserRole).filter(UserRole.name == "admin").first()
    if not admin_role:
        raise HTTPException(status_code=403, detail="Admin role not found")
    
    has_admin = db.query(UserRoleAssignment).filter(
        and_(
            UserRoleAssignment.user_id == current_user.id,
            UserRoleAssignment.role_id == admin_role.id
        )
    ).first()
    
    if not has_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    return True


def check_channel_moderator(current_user: User, channel_id: str, db: Session):
    """Check if user is moderator in channel."""
    try:
        channel_uuid = UUID(channel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel ID")
    
    channel = db.query(Channel).filter(Channel.id == channel_uuid).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    is_creator = channel.creator_id == current_user.id
    
    mod_role = db.query(ChannelRole).filter(
        and_(
            ChannelRole.channel_id == channel_uuid,
            ChannelRole.name == "moderator"
        )
    ).first()
    
    if mod_role:
        has_mod = db.query(ChannelRoleAssignment).filter(
            and_(
                ChannelRoleAssignment.user_id == current_user.id,
                ChannelRoleAssignment.role_id == mod_role.id
            )
        ).first()
        
        if has_mod or is_creator:
            return True
    
    if is_creator:
        return True
    
    raise HTTPException(status_code=403, detail="Moderator privileges required")


# ============ USER ROLES ============

@router.post("/roles", response_model=UserRolePublic, status_code=201)
async def create_role(
    role: UserRoleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new user role (admin only)."""
    check_admin(current_user, db)
    
    logger.info(f"Admin {current_user.username} creating role: {role.name}")
    
    existing = db.query(UserRole).filter(UserRole.name == role.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Role already exists")
    
    new_role = UserRole(
        name=role.name,
        description=role.description,
        permissions=role.permissions
    )
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    
    return new_role


@router.get("/roles", response_model=List[UserRolePublic])
async def list_roles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all user roles."""
    roles = db.query(UserRole).all()
    return roles


@router.post("/users/{user_id}/roles/{role_id}", status_code=201)
async def assign_role_to_user(
    user_id: str,
    role_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign a role to a user (admin only)."""
    check_admin(current_user, db)
    
    try:
        user_uuid = UUID(user_id)
        role_uuid = UUID(role_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    role = db.query(UserRole).filter(UserRole.id == role_uuid).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    existing = db.query(UserRoleAssignment).filter(
        and_(
            UserRoleAssignment.user_id == user_uuid,
            UserRoleAssignment.role_id == role_uuid
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="User already has this role")
    
    assignment = UserRoleAssignment(user_id=user_uuid, role_id=role_uuid)
    db.add(assignment)
    db.commit()
    
    logger.info(f"Role {role.name} assigned to user {user.username} by {current_user.username}")
    
    await cache_service.invalidate_user_cache(user_id)
    
    return {"message": "Role assigned", "user_id": user_id, "role": role.name}


@router.delete("/users/{user_id}/roles/{role_id}", status_code=204)
async def remove_role_from_user(
    user_id: str,
    role_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a role from a user (admin only)."""
    check_admin(current_user, db)
    
    try:
        user_uuid = UUID(user_id)
        role_uuid = UUID(role_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    assignment = db.query(UserRoleAssignment).filter(
        and_(
            UserRoleAssignment.user_id == user_uuid,
            UserRoleAssignment.role_id == role_uuid
        )
    ).first()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Role assignment not found")
    
    db.delete(assignment)
    db.commit()
    
    await cache_service.invalidate_user_cache(user_id)


# ============ CHANNEL ROLES ============

@router.post("/channels/{channel_id}/roles", response_model=ChannelRolePublic, status_code=201)
async def create_channel_role(
    channel_id: str,
    role: ChannelRoleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a channel role (channel creator only)."""
    try:
        channel_uuid = UUID(channel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel ID")
    
    channel = db.query(Channel).filter(Channel.id == channel_uuid).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if channel.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only channel creator can create roles")
    
    existing = db.query(ChannelRole).filter(
        and_(
            ChannelRole.channel_id == channel_uuid,
            ChannelRole.name == role.name
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Role already exists in this channel")
    
    new_role = ChannelRole(
        channel_id=channel_uuid,
        name=role.name,
        permissions=role.permissions
    )
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    
    logger.info(f"Channel role {role.name} created in {channel.name} by {current_user.username}")
    
    return new_role


@router.post("/channels/{channel_id}/members/{user_id}/roles/{role_id}", status_code=201)
async def assign_channel_role(
    channel_id: str,
    user_id: str,
    role_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign a channel role to a user."""
    check_channel_moderator(current_user, channel_id, db)
    
    try:
        channel_uuid = UUID(channel_id)
        user_uuid = UUID(user_id)
        role_uuid = UUID(role_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    role = db.query(ChannelRole).filter(
        and_(
            ChannelRole.id == role_uuid,
            ChannelRole.channel_id == channel_uuid
        )
    ).first()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    existing = db.query(ChannelRoleAssignment).filter(
        and_(
            ChannelRoleAssignment.user_id == user_uuid,
            ChannelRoleAssignment.role_id == role_uuid
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="User already has this role")
    
    assignment = ChannelRoleAssignment(
        user_id=user_uuid,
        channel_id=channel_uuid,
        role_id=role_uuid
    )
    db.add(assignment)
    db.commit()
    
    logger.info(f"Channel role assigned by {current_user.username}")
    
    return {"message": "Channel role assigned"}


# ============ MESSAGE MODERATION ============

@router.post("/flag-content", response_model=FlaggedContentPublic, status_code=201)
async def flag_content(
    flag: FlaggedContentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Flag a message for moderation."""
    try:
        message_uuid = UUID(flag.message_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid message ID")
    
    message = db.query(Message).filter(Message.id == message_uuid).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    flagged = FlaggedContent(
        message_id=message_uuid,
        flagged_by_id=current_user.id,
        reason=flag.reason,
        description=flag.description
    )
    db.add(flagged)
    db.commit()
    db.refresh(flagged)
    
    logger.info(f"Message {message_uuid} flagged by {current_user.username}: {flag.reason}")
    
    return flagged


@router.get("/flagged-content", response_model=List[FlaggedContentPublic])
async def get_flagged_content(
    status: str = "pending",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get flagged content (admin/moderator only)."""
    check_admin(current_user, db)
    
    flags = db.query(FlaggedContent).filter(FlaggedContent.status == status).all()
    return flags


@router.post("/flagged-content/{flag_id}/resolve", status_code=200)
async def resolve_flag(
    flag_id: str,
    action: str = "deleted",  # deleted, warned, suspended, dismissed
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resolve a flagged content report (admin only)."""
    check_admin(current_user, db)
    
    try:
        flag_uuid = UUID(flag_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid flag ID")
    
    flagged = db.query(FlaggedContent).filter(FlaggedContent.id == flag_uuid).first()
    if not flagged:
        raise HTTPException(status_code=404, detail="Flag not found")
    
    flagged.status = "resolved"
    flagged.reviewed_by_id = current_user.id
    flagged.action_taken = action
    flagged.reviewed_at = datetime.utcnow()
    
    # Handle action
    if action == "deleted":
        message = db.query(Message).filter(Message.id == flagged.message_id).first()
        if message:
            message.is_deleted = True
    
    db.commit()
    
    logger.info(f"Flag {flag_id} resolved by {current_user.username} with action: {action}")
    
    return {"message": "Flag resolved", "action": action}


# ============ ADMIN DASHBOARD ============

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get admin dashboard statistics."""
    check_admin(current_user, db)
    
    total_users = db.query(User).count()
    total_channels = db.query(Channel).count()
    total_messages = db.query(Message).count()
    flagged_pending = db.query(FlaggedContent).filter(
        FlaggedContent.status == "pending"
    ).count()
    
    return {
        "total_users": total_users,
        "total_channels": total_channels,
        "total_messages": total_messages,
        "pending_flags": flagged_pending,
    }


@router.get("/dashboard/users")
async def get_users_for_dashboard(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get users for admin dashboard."""
    check_admin(current_user, db)
    
    users = db.query(User).offset(skip).limit(limit).all()
    
    return [
        {
            "id": str(u.id),
            "username": u.username,
            "email": u.email,
            "created_at": u.created_at,
            "status": u.status
        }
        for u in users
    ]


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a user (admin only)."""
    check_admin(current_user, db)
    
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    db.delete(user)
    db.commit()
    
    logger.warning(f"User {user.username} deleted by {current_user.username}")
