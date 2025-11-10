from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User
from app.models.channel import Channel
from app.models.message import Message
from app.utils.websocket_manager import manager
from app.utils.jwt_utils import decode_access_token
import json
from datetime import datetime


router = APIRouter()


@router.websocket("/ws/{channel_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    channel_id: str,
    token: str = Query(...)
):
    """WebSocket endpoint for real-time messaging."""
    
    # Verify token and get user
    try:
        token_data = decode_access_token(token)
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Verify user exists
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if not user:
            await websocket.close(code=4002, reason="User not found")
            return
        
        # Verify channel exists
        channel = db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            await websocket.close(code=4003, reason="Channel not found")
            return
        
        # Verify user is a member of the channel
        if user not in channel.members:
            await websocket.close(code=4004, reason="Not a member of this channel")
            return
        
        # Connect to channel
        await manager.connect(websocket, channel_id)
        
        # Notify others that user joined
        await manager.broadcast_to_channel(
            channel_id,
            {
                "type": "user_joined",
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "email": user.email
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Listen for messages
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Save message to database
            new_message = Message(
                channel_id=channel_id,
                sender_id=user.id,
                content=message_data.get("content", "")
            )
            db.add(new_message)
            db.commit()
            db.refresh(new_message)
            
            # Broadcast message to all clients in channel
            await manager.broadcast_to_channel(
                channel_id,
                {
                    "type": "message",
                    "id": str(new_message.id),
                    "channel_id": channel_id,
                    "sender": {
                        "id": str(user.id),
                        "username": user.username,
                        "email": user.email
                    },
                    "content": new_message.content,
                    "created_at": new_message.created_at.isoformat()
                }
            )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel_id)
        
        # Notify others that user left
        await manager.broadcast_to_channel(
            channel_id,
            {
                "type": "user_left",
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "email": user.email
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, channel_id)
    
    finally:
        db.close()
