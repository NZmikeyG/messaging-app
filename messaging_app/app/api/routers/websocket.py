from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.database import get_db
from app.models.user import User
from app.models.channel import Channel
from app.models.direct_message import DirectMessage
from app.models.user_presence import UserPresence
from app.models.message_read_receipt import MessageReadReceipt
from app.utils.websocket_manager import manager
from app.utils.jwt_utils import decode_token
from app.services.cache_service import cache_service
from datetime import datetime
from uuid import UUID
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ============ CHANNEL WEBSOCKET ============

@router.websocket("/ws/channels/{channel_id}")
async def websocket_channel_endpoint(
    channel_id: str,
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time channel messaging with presence and typing indicators.
    
    Message types:
    - "message": New message in channel
    - "typing": User is typing
    - "stopped_typing": User stopped typing
    - "presence": Update user presence
    - "read_receipt": Message read
    """
    
    user = None
    user_id = None
    
    try:
        # Authenticate user
        payload = decode_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            await websocket.close(code=4001, reason="Invalid user ID format")
            return
        
        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            await websocket.close(code=4001, reason="User not found")
            return
        
        # Check if user is member of channel
        try:
            channel_uuid = UUID(channel_id)
        except ValueError:
            await websocket.close(code=4002, reason="Invalid channel ID format")
            return
        
        channel = db.query(Channel).filter(Channel.id == channel_uuid).first()
        if not channel:
            await websocket.close(code=4002, reason="Channel not found")
            return
        
        if user not in channel.members:
            await websocket.close(code=4003, reason="Not a member of this channel")
            return
        
        logger.info(f"User {user.username} connected to channel {channel.name}")
        
        # Connect to channel
        await manager.connect_to_channel(channel_id, websocket)
        
        # Update user presence
        user_presence = db.query(UserPresence).filter(UserPresence.user_id == user_uuid).first()
        if not user_presence:
            user_presence = UserPresence(user_id=user_uuid, is_online=True, status="online")
            db.add(user_presence)
        else:
            user_presence.is_online = True
            user_presence.status = "online"
            user_presence.last_seen = datetime.utcnow()
        
        db.commit()
        
        # Invalidate presence cache
        await cache_service.invalidate_user_cache(user_id)
        
        # Notify others that user joined
        await manager.broadcast_to_channel(
            channel_id,
            {
                "type": "user_joined",
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "avatar_url": user.avatar_url,
                    "status": user.status
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                # Handle new message
                content = data.get("content", "").strip()
                if not content:
                    await websocket.send_json({"error": "Message content cannot be empty"})
                    continue
                
                logger.info(f"Message from {user.username} in {channel.name}: {content[:50]}...")
                
                await manager.broadcast_to_channel(
                    channel_id,
                    {
                        "type": "message",
                        "data": {
                            "content": content,
                            "sender": {
                                "id": str(user.id),
                                "username": user.username,
                                "email": user.email,
                                "avatar_url": user.avatar_url
                            },
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }
                )
                
                # Stop typing when message sent
                await manager.stop_typing(channel_id, str(user.id))
                
                # Broadcast stopped typing
                await manager.broadcast_to_channel(
                    channel_id,
                    {
                        "type": "stopped_typing",
                        "user_id": str(user.id)
                    }
                )
            
            elif data.get("type") == "typing":
                # User is typing
                await manager.set_typing(channel_id, str(user.id))
                await manager.broadcast_to_channel(
                    channel_id,
                    {
                        "type": "typing_indicator",
                        "user_id": str(user.id),
                        "username": user.username,
                        "typing_users": await manager.get_typing_users(channel_id)
                    }
                )
            
            elif data.get("type") == "stopped_typing":
                # User stopped typing
                await manager.stop_typing(channel_id, str(user.id))
                await manager.broadcast_to_channel(
                    channel_id,
                    {
                        "type": "typing_indicator",
                        "user_id": str(user.id),
                        "typing_users": await manager.get_typing_users(channel_id)
                    }
                )
            
            elif data.get("type") == "presence":
                # Update presence status
                new_status = data.get("status", "online")
                user_presence = db.query(UserPresence).filter(UserPresence.user_id == user_uuid).first()
                if user_presence:
                    user_presence.status = new_status
                    user_presence.last_seen = datetime.utcnow()
                    db.commit()
                    await cache_service.invalidate_user_cache(user_id)
                
                await manager.broadcast_to_channel(
                    channel_id,
                    {
                        "type": "presence_update",
                        "user_id": str(user.id),
                        "username": user.username,
                        "status": new_status
                    }
                )
            
            elif data.get("type") == "read_receipt":
                # Mark message as read
                message_id = data.get("message_id")
                if message_id:
                    try:
                        msg_uuid = UUID(message_id)
                        existing = db.query(MessageReadReceipt).filter(
                            and_(
                                MessageReadReceipt.message_id == msg_uuid,
                                MessageReadReceipt.user_id == user_uuid
                            )
                        ).first()
                        
                        if not existing:
                            receipt = MessageReadReceipt(
                                message_id=msg_uuid,
                                user_id=user_uuid,
                                read_at=datetime.utcnow()
                            )
                            db.add(receipt)
                            db.commit()
                            
                            logger.info(f"Message {message_id} marked as read by {user.username}")
                            
                            await manager.broadcast_to_channel(
                                channel_id,
                                {
                                    "type": "message_read",
                                    "message_id": message_id,
                                    "user_id": str(user.id),
                                    "username": user.username
                                }
                            )
                    except ValueError:
                        logger.error(f"Invalid message ID format: {message_id}")
    
    except Exception as e:
        logger.error(f"WebSocket channel error: {e}", exc_info=True)
    
    finally:
        if user and user_id:
            manager.disconnect_from_channel(channel_id, websocket)
            
            # Update presence to offline
            try:
                user_uuid = UUID(user_id)
                user_presence = db.query(UserPresence).filter(UserPresence.user_id == user_uuid).first()
                if user_presence:
                    user_presence.is_online = False
                    user_presence.status = "offline"
                    user_presence.last_seen = datetime.utcnow()
                    db.commit()
                    await cache_service.invalidate_user_cache(user_id)
            except Exception as e:
                logger.error(f"Error updating presence on disconnect: {e}")
            
            # Notify others that user left
            await manager.broadcast_to_channel(
                channel_id,
                {
                    "type": "user_left",
                    "user_id": str(user.id),
                    "username": user.username,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"User {user.username} disconnected from channel {channel_id}")


# ============ DIRECT MESSAGE WEBSOCKET ============

@router.websocket("/ws/dm/{other_user_id}")
async def websocket_dm_endpoint(
    other_user_id: str,
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time direct messaging with presence and typing.
    
    Message types:
    - "message": New DM
    - "typing": User is typing
    - "stopped_typing": User stopped typing
    - "presence": Update presence
    - "read_receipt": Message read
    """
    
    user = None
    user_id = None
    
    try:
        # Authenticate user
        payload = decode_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        try:
            user_uuid = UUID(user_id)
            other_user_uuid = UUID(other_user_id)
        except ValueError:
            await websocket.close(code=4001, reason="Invalid user ID format")
            return
        
        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            await websocket.close(code=4001, reason="User not found")
            return
        
        other_user = db.query(User).filter(User.id == other_user_uuid).first()
        if not other_user:
            await websocket.close(code=4002, reason="Other user not found")
            return
        
        logger.info(f"User {user.username} connected to DM with {other_user.username}")
        
        # Connect to DM conversation
        await manager.connect_to_dm(str(user.id), other_user_id, websocket)
        
        # Update presence
        user_presence = db.query(UserPresence).filter(UserPresence.user_id == user_uuid).first()
        if not user_presence:
            user_presence = UserPresence(user_id=user_uuid, is_online=True, status="online")
            db.add(user_presence)
        else:
            user_presence.is_online = True
            user_presence.last_seen = datetime.utcnow()
        
        db.commit()
        await cache_service.invalidate_user_cache(user_id)
        
        # Notify other user
        await manager.broadcast_to_dm(
            str(user.id),
            other_user_id,
            {
                "type": "user_joined",
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "avatar_url": user.avatar_url,
                    "status": user.status
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                # Handle new DM
                content = data.get("content", "").strip()
                if not content:
                    await websocket.send_json({"error": "Message content cannot be empty"})
                    continue
                
                logger.info(f"DM from {user.username} to {other_user.username}")
                
                await manager.broadcast_to_dm(
                    str(user.id),
                    other_user_id,
                    {
                        "type": "message",
                        "data": {
                            "content": content,
                            "sender": {
                                "id": str(user.id),
                                "username": user.username,
                                "email": user.email,
                                "avatar_url": user.avatar_url
                            },
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }
                )
                
                # Clear typing indicator
                await manager.broadcast_to_dm(
                    str(user.id),
                    other_user_id,
                    {
                        "type": "stopped_typing",
                        "user_id": str(user.id)
                    }
                )
            
            elif data.get("type") == "typing":
                await manager.broadcast_to_dm(
                    str(user.id),
                    other_user_id,
                    {
                        "type": "typing_indicator",
                        "user_id": str(user.id),
                        "username": user.username
                    }
                )
            
            elif data.get("type") == "stopped_typing":
                await manager.broadcast_to_dm(
                    str(user.id),
                    other_user_id,
                    {
                        "type": "stopped_typing",
                        "user_id": str(user.id)
                    }
                )
            
            elif data.get("type") == "presence":
                # Update presence
                new_status = data.get("status", "online")
                user_presence = db.query(UserPresence).filter(UserPresence.user_id == user_uuid).first()
                if user_presence:
                    user_presence.status = new_status
                    user_presence.last_seen = datetime.utcnow()
                    db.commit()
                    await cache_service.invalidate_user_cache(user_id)
                
                await manager.broadcast_to_dm(
                    str(user.id),
                    other_user_id,
                    {
                        "type": "presence_update",
                        "user_id": str(user.id),
                        "status": new_status
                    }
                )
            
            elif data.get("type") == "read_receipt":
                # Mark message as read
                message_id = data.get("message_id")
                if message_id:
                    try:
                        msg_uuid = UUID(message_id)
                        existing = db.query(MessageReadReceipt).filter(
                            and_(
                                MessageReadReceipt.message_id == msg_uuid,
                                MessageReadReceipt.user_id == user_uuid
                            )
                        ).first()
                        
                        if not existing:
                            receipt = MessageReadReceipt(
                                message_id=msg_uuid,
                                user_id=user_uuid,
                                read_at=datetime.utcnow()
                            )
                            db.add(receipt)
                            db.commit()
                            
                            await manager.broadcast_to_dm(
                                str(user.id),
                                other_user_id,
                                {
                                    "type": "message_read",
                                    "message_id": message_id,
                                    "user_id": str(user.id)
                                }
                            )
                    except ValueError:
                        logger.error(f"Invalid message ID: {message_id}")
    
    except Exception as e:
        logger.error(f"WebSocket DM error: {e}", exc_info=True)
    
    finally:
        if user and user_id:
            manager.disconnect_from_dm(str(user.id), other_user_id, websocket)
            
            # Update presence
            try:
                user_uuid = UUID(user_id)
                user_presence = db.query(UserPresence).filter(UserPresence.user_id == user_uuid).first()
                if user_presence:
                    user_presence.is_online = False
                    user_presence.status = "offline"
                    user_presence.last_seen = datetime.utcnow()
                    db.commit()
                    await cache_service.invalidate_user_cache(user_id)
            except Exception as e:
                logger.error(f"Error updating presence on disconnect: {e}")
            
            await manager.broadcast_to_dm(
                str(user.id),
                other_user_id,
                {
                    "type": "user_left",
                    "user_id": str(user.id),
                    "username": user.username,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"User {user.username} disconnected from DM with {other_user_id}")
