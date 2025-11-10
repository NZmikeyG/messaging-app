from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
import logging

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.user_presence import UserPresence
from app.models.message_read_receipt import MessageReadReceipt
from app.api.schemas.presence import (
    UserPresencePublic, UserPresenceUpdate,
    MessageReadReceiptPublic, MessageReadReceiptCreate
)
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/presence/update", response_model=UserPresencePublic)
async def update_presence(
    presence_update: UserPresenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user presence status."""
    logger.info(f"Updating presence for user {current_user.id}")
    
    user_presence = db.query(UserPresence).filter(
        UserPresence.user_id == current_user.id
    ).first()
    
    if not user_presence:
        user_presence = UserPresence(user_id=current_user.id)
        db.add(user_presence)
    
    if presence_update.is_online is not None:
        user_presence.is_online = presence_update.is_online
    if presence_update.status:
        user_presence.status = presence_update.status
    
    user_presence.last_seen = datetime.utcnow()
    
    db.commit()
    db.refresh(user_presence)
    
    # Invalidate cache
    await cache_service.invalidate_user_cache(str(current_user.id))
    
    return user_presence


@router.get("/presence/{user_id}", response_model=UserPresencePublic)
async def get_presence(
    user_id: str,
    db: Session = Depends(get_db),
):
    """Get user presence status."""
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    # Try cache
    cache_key = f"user:{user_id}:presence"
    cached = await cache_service.get(cache_key)
    if cached:
        return cached
    
    presence = db.query(UserPresence).filter(
        UserPresence.user_id == user_uuid
    ).first()
    
    if not presence:
        raise HTTPException(status_code=404, detail="User presence not found")
    
    # Cache result
    await cache_service.set(cache_key, {
        "user_id": str(presence.user_id),
        "is_online": presence.is_online,
        "status": presence.status,
        "last_seen": presence.last_seen
    }, ttl=60)
    
    return presence


@router.post("/messages/{message_id}/read", response_model=MessageReadReceiptPublic, status_code=201)
async def mark_message_as_read(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a message as read."""
    try:
        msg_uuid = UUID(message_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid message ID format")
    
    logger.info(f"Marking message {message_id} as read by user {current_user.id}")
    
    # Check if receipt already exists
    existing = db.query(MessageReadReceipt).filter(
        MessageReadReceipt.message_id == msg_uuid,
        MessageReadReceipt.user_id == current_user.id,
    ).first()
    
    if existing:
        return existing
    
    receipt = MessageReadReceipt(
        message_id=msg_uuid,
        user_id=current_user.id,
        read_at=datetime.utcnow()
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    
    return receipt


@router.get("/messages/{message_id}/read-receipts")
async def get_read_receipts(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get read receipts for a message."""
    try:
        msg_uuid = UUID(message_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid message ID format")
    
    receipts = db.query(MessageReadReceipt).filter(
        MessageReadReceipt.message_id == msg_uuid
    ).all()
    
    return [
        {
            "user_id": str(r.user_id),
            "read_at": r.read_at
        }
        for r in receipts
    ]
