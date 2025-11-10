import json
import logging
from typing import Set, Dict
from fastapi import WebSocket
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections per channel."""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_channels: Dict[str, Set[str]] = {}  # user_id -> channel_ids
    
    async def connect(self, channel_id: str, websocket: WebSocket, user_id: str):
        """Connect user to channel."""
        await websocket.accept()
        
        if channel_id not in self.active_connections:
            self.active_connections[channel_id] = set()
        
        self.active_connections[channel_id].add(websocket)
        
        if user_id not in self.user_channels:
            self.user_channels[user_id] = set()
        self.user_channels[user_id].add(channel_id)
        
        logger.info(f"User {user_id} connected to channel {channel_id}")
    
    def disconnect(self, channel_id: str, websocket: WebSocket, user_id: str):
        """Disconnect user from channel."""
        if channel_id in self.active_connections:
            self.active_connections[channel_id].discard(websocket)
        
        if user_id in self.user_channels:
            self.user_channels[user_id].discard(channel_id)
        
        logger.info(f"User {user_id} disconnected from channel {channel_id}")
    
    async def broadcast(self, channel_id: str, message: dict):
        """Broadcast message to all users in channel."""
        if channel_id not in self.active_connections:
            return
        
        disconnected = set()
        for connection in self.active_connections[channel_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected
        for connection in disconnected:
            self.active_connections[channel_id].discard(connection)
    
    async def send_typing(self, channel_id: str, user_id: str, username: str):
        """Notify channel that user is typing."""
        message = {
            "type": "typing",
            "user_id": str(user_id),
            "username": username,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast(channel_id, message)
    
    async def send_presence(self, channel_id: str, user_id: str, username: str, is_online: bool):
        """Notify channel of presence change."""
        message = {
            "type": "presence",
            "user_id": str(user_id),
            "username": username,
            "is_online": is_online,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast(channel_id, message)
    
    async def send_read_receipt(self, channel_id: str, user_id: str, message_id: str):
        """Notify channel that message was read."""
        message = {
            "type": "read_receipt",
            "user_id": str(user_id),
            "message_id": str(message_id),
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast(channel_id, message)


# Global connection manager
manager = ConnectionManager()
