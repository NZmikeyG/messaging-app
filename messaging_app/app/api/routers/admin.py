from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, timedelta
import logging
from uuid import UUID

from app.database import get_db
from app.models.admin import (
    AdminAction, UserSuspension, UserRole, ChannelRole, FlaggedContent
)
from app.models.user import User
from app.models.message import Message
from app.models.channel import Channel
from app.api.schemas.admin import (
    UserRoleCreate, UserRoleResponse, ChannelRoleCreate, ChannelRoleResponse,
    FlagMessageRequest, FlaggedContentResponse, ReviewFlagRequest,
    SuspendUserRequest, UserSuspensionResponse, AdminActionResponse,
    AdminDashboardStats
)
from app.dependencies import get_current_user


logger = logging.getLogger(__name__)
router = APIRouter()

# ============ ROLE MANAGEMENT ============

@router.post("/users/{user_id}/role", response_model=UserRoleResponse)
def assign_user_role(
    user_id: UUID,
    role_data: UserRoleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign a user role (Admin only)."""
    # Verify current user is admin
    admin_role = db.query(UserRole).filter(
        UserRole.user_id == current_user.id
    ).first()
    
    if not admin_role or admin_role.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can assign roles"
        )
    
    # Check user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if role already exists
    existing_role = db.query(UserRole).filter(
        UserRole.user_id == user_id
    ).first()
    
    if existing_role:
        # Update existing role
        existing_role.role = role_data.role
        existing_role.assigned_by = current_user.id
        db.commit()
        db.refresh(existing_role)
        
        # Log action
        log_action(
            db, current_user.id, "assign_role", "user", user_id,
            reason=f"Role changed to {role_data.role}"
        )
        
        return existing_role
    
    # Create new role
    new_role = UserRole(
        user_id=user_id,
        role=role_data.role,
        assigned_by=current_user.id
    )
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    
    logger.info(f"User role assigned: {user_id} -> {role_data.role}")
    
    # Log action
    log_action(
        db, current_user.id, "assign_role", "user", user_id,
        reason=f"Role assigned: {role_data.role}"
    )
    
    return new_role


@router.get("/users/{user_id}/role", response_model=UserRoleResponse)
def get_user_role(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a user's role."""
    role = db.query(UserRole).filter(UserRole.user_id == user_id).first()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User role not found"
        )
    
    return role


@router.post("/channels/{channel_id}/members/{user_id}/role", response_model=ChannelRoleResponse)
def assign_channel_role(
    channel_id: UUID,
    user_id: UUID,
    role_data: ChannelRoleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign a channel role (Channel owner/moderator only)."""
    # Check channel exists
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )
    
    # Check current user is channel owner/moderator
    current_channel_role = db.query(ChannelRole).filter(
        and_(
            ChannelRole.channel_id == channel_id,
            ChannelRole.user_id == current_user.id
        )
    ).first()
    
    if not current_channel_role or current_channel_role.role == "member":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only channel owners/moderators can assign roles"
        )
    
    # Check user exists in channel
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if role already exists
    existing_role = db.query(ChannelRole).filter(
        and_(
            ChannelRole.channel_id == channel_id,
            ChannelRole.user_id == user_id
        )
    ).first()
    
    if existing_role:
        existing_role.role = role_data.role
        db.commit()
        db.refresh(existing_role)
        return existing_role
    
    # Create new channel role
    new_role = ChannelRole(
        channel_id=channel_id,
        user_id=user_id,
        role=role_data.role
    )
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    
    logger.info(f"Channel role assigned: {user_id} -> {role_data.role} in {channel_id}")
    
    return new_role


# ============ MESSAGE FLAGGING ============

@router.post("/messages/{message_id}/flag", response_model=FlaggedContentResponse)
def flag_message(
    message_id: UUID,
    flag_data: FlagMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Flag a message for moderation."""
    # Check message exists
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Check if already flagged by this user
    existing_flag = db.query(FlaggedContent).filter(
        and_(
            FlaggedContent.message_id == message_id,
            FlaggedContent.reported_by == current_user.id,
            FlaggedContent.status == "pending"
        )
    ).first()
    
    if existing_flag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already flagged this message"
        )
    
    # Create flag
    flagged = FlaggedContent(
        message_id=message_id,
        reported_by=current_user.id,
        reason=flag_data.reason,
        description=flag_data.description,
        status="pending"
    )
    db.add(flagged)
    db.commit()
    db.refresh(flagged)
    
    logger.info(f"Message flagged: {message_id} by {current_user.id}")
    
    return flagged


@router.get("/flagged-content", response_model=list[FlaggedContentResponse])
def get_flagged_content(
    status: str = "pending",
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get flagged content (Moderators/Admins only)."""
    # Verify current user is moderator or admin
    user_role = db.query(UserRole).filter(
        UserRole.user_id == current_user.id
    ).first()
    
    if not user_role or user_role.role not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only moderators and admins can view flagged content"
        )
    
    # Get flagged content
    flagged = db.query(FlaggedContent).filter(
        FlaggedContent.status == status
    ).order_by(FlaggedContent.created_at.desc()).offset(skip).limit(limit).all()
    
    return flagged


@router.post("/flagged-content/{flag_id}/review", response_model=FlaggedContentResponse)
def review_flagged_content(
    flag_id: UUID,
    review_data: ReviewFlagRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Review and take action on flagged content."""
    # Verify current user is moderator or admin
    user_role = db.query(UserRole).filter(
        UserRole.user_id == current_user.id
    ).first()
    
    if not user_role or user_role.role not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only moderators and admins can review flagged content"
        )
    
    # Get flagged content
    flagged = db.query(FlaggedContent).filter(
        FlaggedContent.id == flag_id
    ).first()
    
    if not flagged:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flagged content not found"
        )
    
    # Update review
    flagged.status = review_data.status
    flagged.reviewed_by = current_user.id
    flagged.reviewed_at = datetime.utcnow()
    flagged.action_taken = review_data.action_taken
    
    # Take action if needed
    if review_data.action_taken == "deleted":
        message = db.query(Message).filter(
            Message.id == flagged.message_id
        ).first()
        if message:
            db.delete(message)
            logger.info(f"Message deleted by moderator: {flagged.message_id}")
    
    elif review_data.action_taken == "warned":
        # Create notification to user about warning
        logger.info(f"User warned: {flagged.message.sender_id}")
    
    elif review_data.action_taken == "suspended":
        # Suspend user
        suspension = db.query(UserSuspension).filter(
            UserSuspension.user_id == flagged.message.sender_id
        ).first()
        
        if not suspension:
            suspension = UserSuspension(
                user_id=flagged.message.sender_id,
                suspended_by=current_user.id,
                reason=flagged.reason,
                suspended_until=datetime.utcnow() + timedelta(days=7)
            )
            db.add(suspension)
        
        logger.info(f"User suspended: {flagged.message.sender_id}")
    
    db.commit()
    db.refresh(flagged)
    
    # Log action
    log_action(
        db, current_user.id, "review_flag", "message", flagged.message_id,
        reason=f"Status: {review_data.status}, Action: {review_data.action_taken}"
    )
    
    return flagged


# ============ USER SUSPENSION ============

@router.post("/users/{user_id}/suspend", response_model=UserSuspensionResponse)
def suspend_user(
    user_id: UUID,
    suspend_data: SuspendUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Suspend a user (Admin only)."""
    # Verify current user is admin
    admin_role = db.query(UserRole).filter(
        UserRole.user_id == current_user.id
    ).first()
    
    if not admin_role or admin_role.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can suspend users"
        )
    
    # Check user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already suspended
    existing_suspension = db.query(UserSuspension).filter(
        and_(
            UserSuspension.user_id == user_id,
            UserSuspension.is_active == True
        )
    ).first()
    
    if existing_suspension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already suspended"
        )
    
    # Create suspension
    suspension = UserSuspension(
        user_id=user_id,
        suspended_by=current_user.id,
        reason=suspend_data.reason,
        suspended_until=suspend_data.suspended_until
    )
    db.add(suspension)
    db.commit()
    db.refresh(suspension)
    
    logger.info(f"User suspended: {user_id}")
    
    # Log action
    log_action(
        db, current_user.id, "suspend_user", "user", user_id,
        reason=suspend_data.reason
    )
    
    return suspension


@router.post("/users/{user_id}/unsuspend")
def unsuspend_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unsuspend a user (Admin only)."""
    # Verify current user is admin
    admin_role = db.query(UserRole).filter(
        UserRole.user_id == current_user.id
    ).first()
    
    if not admin_role or admin_role.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can unsuspend users"
        )
    
    # Get suspension
    suspension = db.query(UserSuspension).filter(
        and_(
            UserSuspension.user_id == user_id,
            UserSuspension.is_active == True
        )
    ).first()
    
    if not suspension:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active suspension found for this user"
        )
    
    # Deactivate suspension
    suspension.is_active = False
    db.commit()
    
    logger.info(f"User unsuspended: {user_id}")
    
    # Log action
    log_action(
        db, current_user.id, "unsuspend_user", "user", user_id,
        reason="Suspension lifted"
    )
    
    return {"message": "User unsuspended successfully"}


# ============ ADMIN DASHBOARD ============

@router.get("/dashboard/stats", response_model=AdminDashboardStats)
def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get admin dashboard statistics (Admin only)."""
    # Verify current user is admin
    admin_role = db.query(UserRole).filter(
        UserRole.user_id == current_user.id
    ).first()
    
    if not admin_role or admin_role.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view dashboard"
        )
    
    # Collect stats
    total_users = db.query(func.count(User.id)).scalar()
    total_channels = db.query(func.count(Channel.id)).scalar()
    total_messages = db.query(func.count(Message.id)).scalar()
    total_flagged = db.query(func.count(FlaggedContent.id)).scalar()
    flagged_pending = db.query(func.count(FlaggedContent.id)).filter(
        FlaggedContent.status == "pending"
    ).scalar()
    total_suspended = db.query(func.count(UserSuspension.id)).filter(
        UserSuspension.is_active == True
    ).scalar()
    
    # Actions today
    today = datetime.utcnow().date()
    admin_actions_today = db.query(func.count(AdminAction.id)).filter(
        func.date(AdminAction.created_at) == today
    ).scalar()
    
    # Flagged by reason
    flagged_reasons = db.query(
        FlaggedContent.reason,
        func.count(FlaggedContent.id).label("count")
    ).filter(
        FlaggedContent.status == "pending"
    ).group_by(FlaggedContent.reason).all()
    
    flagged_by_reason = {reason: count for reason, count in flagged_reasons}
    
    return AdminDashboardStats(
        total_users=total_users or 0,
        total_channels=total_channels or 0,
        total_messages=total_messages or 0,
        total_flagged=total_flagged or 0,
        flagged_pending=flagged_pending or 0,
        total_suspended=total_suspended or 0,
        admin_actions_today=admin_actions_today or 0,
        flagged_by_reason=flagged_by_reason
    )


@router.get("/audit-log", response_model=list[AdminActionResponse])
def get_audit_log(
    action_type: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get admin audit log (Admin only)."""
    # Verify current user is admin
    admin_role = db.query(UserRole).filter(
        UserRole.user_id == current_user.id
    ).first()
    
    if not admin_role or admin_role.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view audit log"
        )
    
    query = db.query(AdminAction)
    
    if action_type:
        query = query.filter(AdminAction.action_type == action_type)
    
    actions = query.order_by(AdminAction.created_at.desc()).offset(skip).limit(limit).all()
    
    return actions


# ============ HELPER FUNCTIONS ============

def log_action(
    db: Session,
    admin_id: UUID,
    action_type: str,
    target_type: str,
    target_id: UUID,
    reason: str = None,
    details: str = None
):
    """Log an admin action for audit trail."""
    action = AdminAction(
        admin_id=admin_id,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        details=details
    )
    db.add(action)
    db.commit()
    logger.info(f"Admin action logged: {action_type} on {target_type} {target_id}")
