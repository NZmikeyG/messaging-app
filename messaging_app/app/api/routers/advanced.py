from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.two_factor_auth import TwoFactorAuth
from app.models.encrypted_message import EncryptedMessage
from app.models.scheduled_message import ScheduledMessage
from app.models.user_analytics import UserAnalytics
from app.models.message import Message
from app.models.channel import Channel
from app.api.schemas.advanced import (
    TwoFactorSetup, TwoFactorVerify,
    EncryptedMessageCreate, ScheduledMessageCreate,
    UserAnalyticsPublic
)
from app.services.two_factor_service import TwoFactorService
from app.services.encryption_service import encryption_service
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ============ TWO-FACTOR AUTHENTICATION ============

@router.post("/2fa/setup", response_model=TwoFactorSetup)
async def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set up two-factor authentication."""
    logger.info(f"Setting up 2FA for user {current_user.username}")
    
    secret, qr_code = TwoFactorService.generate_secret(current_user.username)
    backup_codes = TwoFactorService.generate_backup_codes()
    
    # Store temporarily (user must verify within 15 minutes)
    await cache_service.set(
        f"2fa_temp:{current_user.id}",
        {
            "secret": secret,
            "backup_codes": backup_codes
        },
        ttl=900  # 15 minutes
    )
    
    return {
        "secret_key": secret,
        "qr_code_url": f"data:image/png;base64,{qr_code}"
    }


@router.post("/2fa/verify", status_code=200)
async def verify_2fa(
    verify: TwoFactorVerify,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify and enable 2FA."""
    logger.info(f"Verifying 2FA for user {current_user.username}")
    
    temp_2fa = await cache_service.get(f"2fa_temp:{current_user.id}")
    if not temp_2fa:
        raise HTTPException(status_code=400, detail="2FA setup not initiated")
    
    if not TwoFactorService.verify_totp(temp_2fa["secret"], verify.code):
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    # Save 2FA settings
    twofa = db.query(TwoFactorAuth).filter(TwoFactorAuth.user_id == current_user.id).first()
    if not twofa:
        twofa = TwoFactorAuth(
            user_id=current_user.id,
            secret_key=temp_2fa["secret"],
            backup_codes=",".join(temp_2fa["backup_codes"])
        )
        db.add(twofa)
    else:
        twofa.secret_key = temp_2fa["secret"]
        twofa.backup_codes = ",".join(temp_2fa["backup_codes"])
    
    twofa.is_enabled = True
    db.commit()
    
    # Clear temporary cache
    await cache_service.delete(f"2fa_temp:{current_user.id}")
    
    return {"message": "2FA enabled successfully", "backup_codes": temp_2fa["backup_codes"]}


@router.post("/2fa/disable", status_code=200)
async def disable_2fa(
    verify: TwoFactorVerify,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable 2FA."""
    logger.warning(f"Disabling 2FA for user {current_user.username}")
    
    twofa = db.query(TwoFactorAuth).filter(TwoFactorAuth.user_id == current_user.id).first()
    if not twofa or not twofa.is_enabled:
        raise HTTPException(status_code=400, detail="2FA not enabled")
    
    if not TwoFactorService.verify_totp(twofa.secret_key, verify.code):
        raise HTTPException(status_code=400, detail="Invalid code")
    
    twofa.is_enabled = False
    db.commit()
    
    return {"message": "2FA disabled"}


# ============ MESSAGE ENCRYPTION ============

@router.post("/messages/{message_id}/encrypt", status_code=200)
async def encrypt_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Encrypt a message."""
    try:
        msg_uuid = UUID(message_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid message ID")
    
    message = db.query(Message).filter(Message.id == msg_uuid).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if message.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only encrypt your own messages")
    
    try:
        encrypted_content, salt = encryption_service.encrypt_message(message.content)
        
        encrypted_msg = EncryptedMessage(
            message_id=msg_uuid,
            encrypted_content=encrypted_content
        )
        db.add(encrypted_msg)
        db.commit()
        
        logger.info(f"Message {message_id} encrypted")
        
        return {"message": "Message encrypted", "encrypted": True}
    
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        raise HTTPException(status_code=500, detail="Encryption failed")


# ============ SCHEDULED MESSAGES ============

@router.post("/messages/schedule", response_model=dict, status_code=201)
async def schedule_message(
    scheduled: ScheduledMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Schedule a message to be sent later."""
    logger.info(f"Scheduling message by user {current_user.username}")
    
    if scheduled.scheduled_for < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Cannot schedule in the past")
    
    if scheduled.channel_id:
        try:
            channel_uuid = UUID(scheduled.channel_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid channel ID")
        
        channel = db.query(Channel).filter(Channel.id == channel_uuid).first()
        if not channel or current_user not in channel.members:
            raise HTTPException(status_code=403, detail="Not a member of this channel")
    
    scheduled_msg = ScheduledMessage(
        user_id=current_user.id,
        channel_id=UUID(scheduled.channel_id) if scheduled.channel_id else None,
        recipient_id=UUID(scheduled.recipient_id) if scheduled.recipient_id else None,
        content=scheduled.content,
        scheduled_for=scheduled.scheduled_for
    )
    db.add(scheduled_msg)
    db.commit()
    db.refresh(scheduled_msg)
    
    return {
        "message": "Message scheduled",
        "scheduled_id": str(scheduled_msg.id),
        "scheduled_for": scheduled_msg.scheduled_for
    }


@router.get("/messages/scheduled")
async def get_scheduled_messages(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's scheduled messages."""
    scheduled = db.query(ScheduledMessage).filter(
        ScheduledMessage.user_id == current_user.id,
        ScheduledMessage.is_sent == False
    ).all()
    
    return [
        {
            "id": str(s.id),
            "content": s.content,
            "channel_id": str(s.channel_id) if s.channel_id else None,
            "recipient_id": str(s.recipient_id) if s.recipient_id else None,
            "scheduled_for": s.scheduled_for
        }
        for s in scheduled
    ]


@router.delete("/messages/scheduled/{scheduled_id}", status_code=204)
async def cancel_scheduled_message(
    scheduled_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a scheduled message."""
    try:
        sched_uuid = UUID(scheduled_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scheduled message ID")
    
    scheduled = db.query(ScheduledMessage).filter(
        ScheduledMessage.id == sched_uuid,
        ScheduledMessage.user_id == current_user.id
    ).first()
    
    if not scheduled:
        raise HTTPException(status_code=404, detail="Scheduled message not found")
    
    if scheduled.is_sent:
        raise HTTPException(status_code=400, detail="Message already sent")
    
    db.delete(scheduled)
    db.commit()


# ============ USER ANALYTICS ============

@router.get("/analytics/me", response_model=UserAnalyticsPublic)
async def get_my_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's analytics."""
    cache_key = f"analytics:{current_user.id}"
    
    cached = await cache_service.get(cache_key)
    if cached:
        return cached
    
    analytics = db.query(UserAnalytics).filter(
        UserAnalytics.user_id == current_user.id
    ).first()
    
    if not analytics:
        analytics = UserAnalytics(user_id=current_user.id)
        db.add(analytics)
        db.commit()
        db.refresh(analytics)
    
    result = {
        "user_id": str(analytics.user_id),
        "total_messages_sent": analytics.total_messages_sent,
        "total_dms_sent": analytics.total_dms_sent,
        "channels_joined": analytics.channels_joined,
        "total_reactions": analytics.total_reactions,
        "avg_message_length": analytics.avg_message_length,
        "last_active": analytics.last_active,
        "login_count": analytics.login_count
    }
    
    await cache_service.set(cache_key, result, ttl=300)
    return result


@router.get("/analytics/users/{user_id}", response_model=UserAnalyticsPublic)
async def get_user_analytics(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get any user's public analytics (admin only)."""
    # Check admin privilege
    from app.api.routers.admin import check_admin
    check_admin(current_user, db)
    
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    analytics = db.query(UserAnalytics).filter(
        UserAnalytics.user_id == user_uuid
    ).first()
    
    if not analytics:
        raise HTTPException(status_code=404, detail="Analytics not found")
    
    return analytics
