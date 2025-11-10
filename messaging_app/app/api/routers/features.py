from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from uuid import UUID
from typing import List
import logging
import secrets
from datetime import datetime, timedelta

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.models.user_block import UserBlock
from app.models.pinned_message import PinnedMessage
from app.models.channel_archive import ChannelArchive
from app.models.user_preferences import UserPreferences
from app.models.api_key import APIKey
from app.models.message import Message
from app.models.channel import Channel
from app.models.direct_message import DirectMessage
from app.api.schemas.features import (
    NotificationCreate, NotificationPublic,
    UserBlockCreate, UserBlockPublic,
    PinnedMessageCreate, PinnedMessagePublic,
    UserPreferencesUpdate, UserPreferencesPublic,
    APIKeyCreate, APIKeyPublic
)
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ============ NOTIFICATIONS ============

@router.get("/notifications", response_model=List[NotificationPublic])
async def get_notifications(
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user notifications."""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    notifications = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    return notifications


@router.post("/notifications/{notification_id}/read", status_code=200)
async def mark_notification_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark notification as read."""
    try:
        notif_uuid = UUID(notification_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification ID")
    
    notification = db.query(Notification).filter(
        and_(
            Notification.id == notif_uuid,
            Notification.user_id == current_user.id
        )
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    db.commit()
    
    return {"message": "Notification marked as read"}


@router.post("/notifications/read-all", status_code=200)
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read."""
    db.query(Notification).filter(
        and_(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        )
    ).update({Notification.is_read: True})
    
    db.commit()
    return {"message": "All notifications marked as read"}


# ============ USER BLOCKING ============

@router.post("/block", response_model=UserBlockPublic, status_code=201)
async def block_user(
    block: UserBlockCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Block a user."""
    try:
        blocked_uuid = UUID(block.blocked_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    if blocked_uuid == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot block yourself")
    
    existing = db.query(UserBlock).filter(
        and_(
            UserBlock.blocker_id == current_user.id,
            UserBlock.blocked_id == blocked_uuid
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="User already blocked")
    
    user_block = UserBlock(
        blocker_id=current_user.id,
        blocked_id=blocked_uuid
    )
    db.add(user_block)
    db.commit()
    db.refresh(user_block)
    
    logger.info(f"User {current_user.username} blocked user {block.blocked_id}")
    
    return user_block


@router.delete("/block/{user_id}", status_code=204)
async def unblock_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unblock a user."""
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    user_block = db.query(UserBlock).filter(
        and_(
            UserBlock.blocker_id == current_user.id,
            UserBlock.blocked_id == user_uuid
        )
    ).first()
    
    if not user_block:
        raise HTTPException(status_code=404, detail="User not blocked")
    
    db.delete(user_block)
    db.commit()


@router.get("/blocked-users")
async def get_blocked_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of blocked users."""
    blocks = db.query(UserBlock).filter(UserBlock.blocker_id == current_user.id).all()
    
    return [
        {
            "user_id": str(b.blocked_id),
            "username": b.blocked.username,
            "blocked_at": b.created_at
        }
        for b in blocks
    ]


# ============ MESSAGE PINNING ============

@router.post("/messages/{message_id}/pin", response_model=PinnedMessagePublic, status_code=201)
async def pin_message(
    message_id: str,
    channel_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Pin a message in a channel."""
    try:
        msg_uuid = UUID(message_id)
        chan_uuid = UUID(channel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    message = db.query(Message).filter(Message.id == msg_uuid).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    channel = db.query(Channel).filter(Channel.id == chan_uuid).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Check if user is channel creator or moderator
    if channel.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only channel creator can pin messages")
    
    existing = db.query(PinnedMessage).filter(PinnedMessage.message_id == msg_uuid).first()
    if existing:
        raise HTTPException(status_code=400, detail="Message already pinned")
    
    pinned = PinnedMessage(
        message_id=msg_uuid,
        channel_id=chan_uuid,
        pinned_by_id=current_user.id
    )
    db.add(pinned)
    db.commit()
    db.refresh(pinned)
    
    await cache_service.invalidate_channel_cache(channel_id)
    
    return pinned


@router.delete("/messages/{message_id}/unpin", status_code=204)
async def unpin_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unpin a message."""
    try:
        msg_uuid = UUID(message_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid message ID")
    
    pinned = db.query(PinnedMessage).filter(PinnedMessage.message_id == msg_uuid).first()
    if not pinned:
        raise HTTPException(status_code=404, detail="Message not pinned")
    
    if pinned.pinned_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only who pinned can unpin")
    
    db.delete(pinned)
    db.commit()
    
    await cache_service.invalidate_channel_cache(str(pinned.channel_id))


@router.get("/channels/{channel_id}/pinned-messages", response_model=List[PinnedMessagePublic])
async def get_pinned_messages(
    channel_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get pinned messages in channel."""
    try:
        chan_uuid = UUID(channel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel ID")
    
    pinned = db.query(PinnedMessage).filter(PinnedMessage.channel_id == chan_uuid).all()
    return pinned


# ============ CHANNEL ARCHIVE ============

@router.post("/channels/{channel_id}/archive", status_code=200)
async def archive_channel(
    channel_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Archive a channel."""
    try:
        chan_uuid = UUID(channel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel ID")
    
    channel = db.query(Channel).filter(Channel.id == chan_uuid).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if channel.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only creator can archive")
    
    existing = db.query(ChannelArchive).filter(ChannelArchive.channel_id == chan_uuid).first()
    if existing and existing.is_archived:
        raise HTTPException(status_code=400, detail="Channel already archived")
    
    if existing:
        existing.is_archived = True
    else:
        archive = ChannelArchive(
            channel_id=chan_uuid,
            archived_by_id=current_user.id
        )
        db.add(archive)
    
    db.commit()
    await cache_service.invalidate_channel_cache(channel_id)
    
    return {"message": "Channel archived"}


@router.post("/channels/{channel_id}/unarchive", status_code=200)
async def unarchive_channel(
    channel_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unarchive a channel."""
    try:
        chan_uuid = UUID(channel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel ID")
    
    channel = db.query(Channel).filter(Channel.id == chan_uuid).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if channel.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only creator can unarchive")
    
    archive = db.query(ChannelArchive).filter(ChannelArchive.channel_id == chan_uuid).first()
    if not archive or not archive.is_archived:
        raise HTTPException(status_code=400, detail="Channel not archived")
    
    archive.is_archived = False
    db.commit()
    await cache_service.invalidate_channel_cache(channel_id)
    
    return {"message": "Channel unarchived"}


# ============ USER PREFERENCES ============

@router.get("/preferences", response_model=UserPreferencesPublic)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user preferences."""
    cache_key = f"preferences:{current_user.id}"
    cached = await cache_service.get(cache_key)
    if cached:
        return cached
    
    prefs = db.query(UserPreferences).filter(UserPreferences.user_id == current_user.id).first()
    if not prefs:
        prefs = UserPreferences(user_id=current_user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    
    result = {
        "theme": prefs.theme,
        "notifications_enabled": prefs.notifications_enabled,
        "email_notifications": prefs.email_notifications,
        "privacy_level": prefs.privacy_level,
        "show_online_status": prefs.show_online_status,
        "allow_dm_from": prefs.allow_dm_from
    }
    
    await cache_service.set(cache_key, result, ttl=3600)
    return result


@router.put("/preferences", response_model=UserPreferencesPublic)
async def update_preferences(
    prefs_update: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user preferences."""
    prefs = db.query(UserPreferences).filter(UserPreferences.user_id == current_user.id).first()
    if not prefs:
        prefs = UserPreferences(user_id=current_user.id)
        db.add(prefs)
    
    if prefs_update.theme:
        prefs.theme = prefs_update.theme
    if prefs_update.notifications_enabled is not None:
        prefs.notifications_enabled = prefs_update.notifications_enabled
    if prefs_update.email_notifications is not None:
        prefs.email_notifications = prefs_update.email_notifications
    if prefs_update.privacy_level:
        prefs.privacy_level = prefs_update.privacy_level
    if prefs_update.show_online_status is not None:
        prefs.show_online_status = prefs_update.show_online_status
    if prefs_update.allow_dm_from:
        prefs.allow_dm_from = prefs_update.allow_dm_from
    
    db.commit()
    db.refresh(prefs)
    
    await cache_service.invalidate_user_cache(str(current_user.id))
    
    return prefs


# ============ API KEYS ============

@router.post("/api-keys", response_model=APIKeyPublic, status_code=201)
async def create_api_key(
    key_create: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create API key for current user."""
    api_key = APIKey(
        user_id=current_user.id,
        key=f"sk_{secrets.token_urlsafe(32)}",
        name=key_create.name,
        expires_at=key_create.expires_at
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    logger.info(f"API key created for user {current_user.username}")
    
    return api_key


@router.get("/api-keys", response_model=List[APIKeyPublic])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List API keys for current user."""
    keys = db.query(APIKey).filter(APIKey.user_id == current_user.id).all()
    return keys


@router.delete("/api-keys/{key_id}", status_code=204)
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete API key."""
    try:
        key_uuid = UUID(key_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid key ID")
    
    api_key = db.query(APIKey).filter(
        and_(
            APIKey.id == key_uuid,
            APIKey.user_id == current_user.id
        )
    ).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    db.delete(api_key)
    db.commit()


# ============ SEARCH ============

@router.get("/search")
async def search(
    query: str,
    type: str = "all",  # all, messages, channels, users
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Full-text search across messages, channels, and users."""
    results = {"messages": [], "channels": [], "users": []}
    
    if type in ["all", "messages"]:
        messages = db.query(Message).filter(
            Message.content.ilike(f"%{query}%"),
            Message.is_deleted == False
        ).offset(skip).limit(limit).all()
        results["messages"] = [
            {
                "id": str(m.id),
                "content": m.content[:100],
                "user": m.user.username,
                "channel_id": str(m.channel_id),
                "created_at": m.created_at
            }
            for m in messages
        ]
    
    if type in ["all", "channels"]:
        channels = db.query(Channel).filter(
            or_(
                Channel.name.ilike(f"%{query}%"),
                Channel.description.ilike(f"%{query}%")
            )
        ).offset(skip).limit(limit).all()
        results["channels"] = [
            {
                "id": str(c.id),
                "name": c.name,
                "description": c.description,
                "member_count": len(c.members)
            }
            for c in channels if current_user in c.members
        ]
    
    if type in ["all", "users"]:
        users = db.query(User).filter(
            or_(
                User.username.ilike(f"%{query}%"),
                User.email.ilike(f"%{query}%")
            )
        ).offset(skip).limit(limit).all()
        results["users"] = [
            {
                "id": str(u.id),
                "username": u.username,
                "email": u.email,
                "avatar_url": u.avatar_url
            }
            for u in users
        ]
    
    return results
