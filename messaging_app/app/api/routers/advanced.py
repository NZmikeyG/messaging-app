from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from datetime import datetime, timedelta
import logging
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.models.message import Message
from app.models.channel import Channel
from app.models.advanced import (
    TwoFactorAuth, DeviceSession, UserActivity, SecurityAuditLog, SearchIndex
)
from app.api.schemas.advanced import (
    TwoFactorSetupResponse, TwoFactorVerifyRequest, DeviceSessionResponse,
    UserActivityResponse, SecurityAuditLogResponse, AdvancedSearchRequest,
    AdvancedSearchResult, UserAnalyticsResponse, AdminAnalyticsDashboard
)
from app.dependencies import get_current_user
from app.utils.security import hash_password, verify_password
from app.utils.totp import TOTPManager
from app.models.admin import UserRole
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# ============ 2FA MANAGEMENT ============

@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Setup two-factor authentication for user."""
    # Check if 2FA already enabled
    twofa = db.query(TwoFactorAuth).filter(
        TwoFactorAuth.user_id == current_user.id
    ).first()
    
    if twofa and twofa.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA already enabled"
        )
    
    # Generate secret
    secret = TOTPManager.generate_secret()
    backup_codes = TOTPManager.generate_backup_codes()
    
    # Generate QR code
    qr_code = TOTPManager.generate_qr_code(secret, current_user.email)
    
    # Store temporary secret (not enabled yet)
    if twofa:
        twofa.secret = secret
        twofa.backup_codes = ",".join(backup_codes)
    else:
        twofa = TwoFactorAuth(
            user_id=current_user.id,
            secret=secret,
            backup_codes=",".join(backup_codes),
            is_enabled=False
        )
        db.add(twofa)
    
    db.commit()
    
    logger.info(f"2FA setup initiated for user: {current_user.id}")
    
    return TwoFactorSetupResponse(
        secret=secret,
        qr_code=f"data:image/png;base64,{qr_code}",
        backup_codes=backup_codes
    )


@router.post("/2fa/verify")
def verify_2fa(
    verify_data: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify and enable 2FA."""
    twofa = db.query(TwoFactorAuth).filter(
        TwoFactorAuth.user_id == current_user.id
    ).first()
    
    if not twofa or not twofa.secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA not setup"
        )
    
    # Verify TOTP code
    if not TOTPManager.verify_token(twofa.secret, verify_data.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA code"
        )
    
    # Enable 2FA
    twofa.is_enabled = True
    twofa.enabled_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"2FA enabled for user: {current_user.id}")
    
    # Log security event
    log_security_event(
        db, current_user.id, "2fa_enabled", "success", None
    )
    
    return {"message": "2FA enabled successfully"}


@router.post("/2fa/disable")
def disable_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable 2FA."""
    twofa = db.query(TwoFactorAuth).filter(
        TwoFactorAuth.user_id == current_user.id
    ).first()
    
    if not twofa or not twofa.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA not enabled"
        )
    
    # Disable 2FA
    twofa.is_enabled = False
    db.commit()
    
    logger.info(f"2FA disabled for user: {current_user.id}")
    
    # Log security event
    log_security_event(
        db, current_user.id, "2fa_disabled", "success", None
    )
    
    return {"message": "2FA disabled successfully"}


# ============ DEVICE MANAGEMENT ============

@router.get("/devices", response_model=list[DeviceSessionResponse])
def get_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all active devices for current user."""
    devices = db.query(DeviceSession).filter(
        and_(
            DeviceSession.user_id == current_user.id,
            DeviceSession.is_active == True
        )
    ).all()
    
    return devices


@router.post("/devices", response_model=DeviceSessionResponse)
def register_device(
    device_name: str,
    device_type: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register a new device."""
    # Get IP address and user agent
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent", "")
    
    # Create device session
    device = DeviceSession(
        user_id=current_user.id,
        device_name=device_name,
        device_type=device_type,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    
    logger.info(f"Device registered: {current_user.id} - {device_name}")
    
    return device


@router.delete("/devices/{device_id}")
def remove_device(
    device_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a device session."""
    device = db.query(DeviceSession).filter(
        and_(
            DeviceSession.id == device_id,
            DeviceSession.user_id == current_user.id
        )
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    device.is_active = False
    db.commit()
    
    logger.info(f"Device removed: {current_user.id} - {device.device_name}")
    
    return {"message": "Device removed successfully"}


# ============ ADVANCED SEARCH ============

@router.post("/search", response_model=list[AdvancedSearchResult])
def advanced_search(
    search_req: AdvancedSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Advanced search for messages and channels."""
    results = []
    query = search_req.query.lower()
    
    # Search messages
    if search_req.search_type in ["all", "messages"]:
        messages = db.query(Message).filter(
            Message.content.ilike(f"%{query}%")
        ).limit(search_req.limit).offset(search_req.offset).all()
        
        for msg in messages:
            results.append(AdvancedSearchResult(
                type="message",
                id=msg.id,
                title=f"Message from {msg.sender.username}",
                preview=msg.content[:100],
                relevance_score=0.9,
                created_at=msg.created_at
            ))
    
    # Search channels
    if search_req.search_type in ["all", "channels"]:
        channels = db.query(Channel).filter(
            Channel.name.ilike(f"%{query}%")
        ).limit(search_req.limit).offset(search_req.offset).all()
        
        for ch in channels:
            results.append(AdvancedSearchResult(
                type="channel",
                id=ch.id,
                title=ch.name,
                preview=ch.description or "No description",
                relevance_score=0.95,
                created_at=ch.created_at
            ))
    
    # Sort by relevance and date
    results.sort(key=lambda x: (-x.relevance_score, -x.created_at.timestamp()))
    
    return results


# ============ ANALYTICS ============

@router.get("/analytics/user", response_model=UserAnalyticsResponse)
def get_user_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analytics for current user."""
    # Total messages sent
    total_messages = db.query(func.count(Message.id)).filter(
        Message.sender_id == current_user.id
    ).scalar() or 0
    
    # Messages last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    messages_30days = db.query(func.count(Message.id)).filter(
        and_(
            Message.sender_id == current_user.id,
            Message.created_at >= thirty_days_ago
        )
    ).scalar() or 0
    
    # Average messages per day
    avg_per_day = messages_30days / 30 if messages_30days > 0 else 0
    
    # Total channels joined
    total_channels = db.query(func.count(Channel.id)).filter(
        Channel.created_by == current_user.id
    ).scalar() or 0
    
    # Active devices
    active_devices = db.query(func.count(DeviceSession.id)).filter(
        and_(
            DeviceSession.user_id == current_user.id,
            DeviceSession.is_active == True
        )
    ).scalar() or 0
    
    # Last active
    last_activity = db.query(UserActivity).filter(
        UserActivity.user_id == current_user.id
    ).order_by(desc(UserActivity.created_at)).first()
    
    last_active = last_activity.created_at if last_activity else current_user.created_at
    
    return UserAnalyticsResponse(
        user_id=current_user.id,
        total_messages_sent=total_messages,
        total_channels_joined=total_channels,
        average_messages_per_day=avg_per_day,
        most_active_channel=None,
        last_active=last_active,
        devices_active=active_devices
    )


@router.get("/analytics/dashboard", response_model=AdminAnalyticsDashboard)
def get_admin_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get admin analytics dashboard (Admin only)."""
    # Verify admin
    user_role = db.query(UserRole).filter(
        UserRole.user_id == current_user.id
    ).first()
    
    if not user_role or user_role.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view dashboard"
        )
    
    today = datetime.utcnow().date()
    
    # Users active today
    active_today = db.query(func.count(UserActivity.id)).filter(
        func.date(UserActivity.created_at) == today
    ).scalar() or 0
    
    # Messages today
    messages_today = db.query(func.count(Message.id)).filter(
        func.date(Message.created_at) == today
    ).scalar() or 0
    
    # Channels created today
    channels_today = db.query(func.count(Channel.id)).filter(
        func.date(Channel.created_at) == today
    ).scalar() or 0
    
    # Security events today
    security_events = db.query(func.count(SecurityAuditLog.id)).filter(
        func.date(SecurityAuditLog.created_at) == today
    ).scalar() or 0
    
    # Failed logins
    failed_logins = db.query(func.count(SecurityAuditLog.id)).filter(
        and_(
            func.date(SecurityAuditLog.created_at) == today,
            SecurityAuditLog.status == "failure",
            SecurityAuditLog.event_type == "login"
        )
    ).scalar() or 0
    
    # 2FA enabled users
    twofa_enabled = db.query(func.count(TwoFactorAuth.id)).filter(
        TwoFactorAuth.is_enabled == True
    ).scalar() or 0
    
    return AdminAnalyticsDashboard(
        total_users_active_today=active_today,
        total_messages_today=messages_today,
        average_response_time_ms=150.0,
        channels_created_today=channels_today,
        security_events_today=security_events,
        failed_logins_today=failed_logins,
        two_fa_enabled_users=twofa_enabled,
        peak_hour=14,
        engagement_rate=0.75
    )


# ============ SECURITY AUDIT ============

@router.get("/security/audit-log", response_model=list[SecurityAuditLogResponse])
def get_security_log(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get security audit log for current user."""
    logs = db.query(SecurityAuditLog).filter(
        SecurityAuditLog.user_id == current_user.id
    ).order_by(desc(SecurityAuditLog.created_at)).offset(skip).limit(limit).all()
    
    return logs


# ============ HELPER FUNCTIONS ============

def log_security_event(
    db: Session,
    user_id: UUID,
    event_type: str,
    status: str,
    request: Request = None,
    reason: str = None
):
    """Log a security event."""
    ip_address = None
    user_agent = None
    
    if request:
        ip_address = request.client.host
        user_agent = request.headers.get("user-agent")
    
    audit_log = SecurityAuditLog(
        user_id=user_id,
        event_type=event_type,
        ip_address=ip_address,
        user_agent=user_agent,
        status=status,
        reason=reason
    )
    db.add(audit_log)
    db.commit()
    
    logger.info(f"Security event: {event_type} for {user_id} - {status}")


def log_user_activity(
    db: Session,
    user_id: UUID,
    action: str,
    target_type: str,
    target_id: UUID = None,
    metadata_payload: dict = None
):
    """Log user activity for analytics."""
    activity = UserActivity(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata_payload_payload=metadata_payload
    )
    db.add(activity)
    db.commit()
    
    logger.info(f"User activity: {action} for {user_id}")

