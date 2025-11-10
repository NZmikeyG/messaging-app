from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.channel import Channel
from app.models.direct_message import DirectMessage
from app.utils.websocket_manager import manager
from app.utils.jwt_utils import decode_token
from datetime import datetime
import json


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
    WebSocket endpoint for real-time channel messaging.
    
    Message types:
    - "message": New message in channel
    - "typing": User is typing
    - "stopped_typing": User stopped typing
    """
    
    try:
        # Authenticate user
        payload = decode_token(token)
        user_id = payload.get("sub")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await websocket.close(code=4001, reason="User not found")
            return
        
        # Check if user is member of channel
        channel = db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            await websocket.close(code=4002, reason="Channel not found")
            return
        
        if user not in channel.members:
            await websocket.close(code=4003, reason="Not a member of this channel")
            return
        
        # Connect to channel
        await manager.connect_to_channel(channel_id, websocket)
        
        # Notify others that user joined
        await manager.broadcast_to_channel(
            channel_id,
            {
                "type": "user_joined",
                "user": {
                    "id": str(user.id),
                    "username": user.username
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                # Handle new message
                await manager.broadcast_to_channel(
                    channel_id,
                    {
                        "type": "message",
                        "data": {
                            "content": data.get("content"),
                            "sender": {
                                "id": str(user.id),
                                "username": user.username,
                                "email": user.email
                            },
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }
                )
                # Stop typing when message sent
                await manager.stop_typing(channel_id, str(user.id))
            
            elif data.get("type") == "typing":
                # User is typing
                await manager.set_typing(channel_id, str(user.id))
                await manager.broadcast_to_channel(
                    channel_id,
                    {
                        "type": "typing",
                        "user_id": str(user.id),
                        "username": user.username
                    }
                )
            
            elif data.get("type") == "stopped_typing":
                # User stopped typing
                await manager.stop_typing(channel_id, str(user.id))
                await manager.broadcast_to_channel(
                    channel_id,
                    {
                        "type": "stopped_typing",
                        "user_id": str(user.id)
                    }
                )
    
    except Exception as e:
        print(f"WebSocket error: {e}")
    
    finally:
        manager.disconnect_from_channel(channel_id, websocket)
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


# ============ DIRECT MESSAGE WEBSOCKET ============

@router.websocket("/ws/dm/{other_user_id}")
async def websocket_dm_endpoint(
    other_user_id: str,
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time direct messaging.
    
    Message types:
    - "message": New DM
    - "typing": User is typing
    - "stopped_typing": User stopped typing
    """
    
    try:
        # Authenticate user
        payload = decode_token(token)
        user_id = payload.get("sub")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await websocket.close(code=4001, reason="User not found")
            return
        
        other_user = db.query(User).filter(User.id == other_user_id).first()
        if not other_user:
            await websocket.close(code=4002, reason="Other user not found")
            return
        
        # Connect to DM conversation
        await manager.connect_to_dm(str(user.id), other_user_id, websocket)
        
        # Notify other user that this user joined
        await manager.broadcast_to_dm(
            str(user.id),
            other_user_id,
            {
                "type": "user_joined",
                "user": {
                    "id": str(user.id),
                    "username": user.username
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                # Handle new DM
                await manager.broadcast_to_dm(
                    str(user.id),
                    other_user_id,
                    {
                        "type": "message",
                        "data": {
                            "content": data.get("content"),
                            "sender": {
                                "id": str(user.id),
                                "username": user.username,
                                "email": user.email
                            },
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }
                )
            
            elif data.get("type") == "typing":
                await manager.broadcast_to_dm(
                    str(user.id),
                    other_user_id,
                    {
                        "type": "typing",
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
    
    except Exception as e:
        print(f"WebSocket DM error: {e}")
    
    finally:
        manager.disconnect_from_dm(str(user.id), other_user_id, websocket)
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
