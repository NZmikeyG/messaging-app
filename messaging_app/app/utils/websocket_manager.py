from typing import List, Dict, Set
from fastapi import WebSocket
import json


class WebSocketManager:
    def __init__(self):
        # Store active connections per channel
        self.active_channel_connections: Dict[str, List[WebSocket]] = {}
        # Store active connections per DM conversation
        self.active_dm_connections: Dict[str, List[WebSocket]] = {}
        # Track user typing status
        self.typing_users: Dict[str, Set[str]] = {}

    # ============ CHANNEL WEBSOCKETS ============

    async def connect_to_channel(self, channel_id: str, websocket: WebSocket):
        """Add a connection to a channel."""
        await websocket.accept()
        if channel_id not in self.active_channel_connections:
            self.active_channel_connections[channel_id] = []
        self.active_channel_connections[channel_id].append(websocket)

    def disconnect_from_channel(self, channel_id: str, websocket: WebSocket):
        """Remove a connection from a channel."""
        if channel_id in self.active_channel_connections:
            self.active_channel_connections[channel_id].remove(websocket)
            if not self.active_channel_connections[channel_id]:
                del self.active_channel_connections[channel_id]

    async def broadcast_to_channel(self, channel_id: str, message: dict):
        """Broadcast a message to all users in a channel."""
        if channel_id in self.active_channel_connections:
            for connection in self.active_channel_connections[channel_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error sending message: {e}")

    # ============ DIRECT MESSAGE WEBSOCKETS ============

    def get_dm_conversation_key(self, user_id_1: str, user_id_2: str) -> str:
        """Generate a unique key for a DM conversation."""
        ids = sorted([user_id_1, user_id_2])
        return f"dm_{ids[0]}_{ids[1]}"

    async def connect_to_dm(self, user_id_1: str, user_id_2: str, websocket: WebSocket):
        """Add a connection to a DM conversation."""
        await websocket.accept()
        conversation_key = self.get_dm_conversation_key(user_id_1, user_id_2)
        if conversation_key not in self.active_dm_connections:
            self.active_dm_connections[conversation_key] = []
        self.active_dm_connections[conversation_key].append(websocket)

    def disconnect_from_dm(self, user_id_1: str, user_id_2: str, websocket: WebSocket):
        """Remove a connection from a DM conversation."""
        conversation_key = self.get_dm_conversation_key(user_id_1, user_id_2)
        if conversation_key in self.active_dm_connections:
            self.active_dm_connections[conversation_key].remove(websocket)
            if not self.active_dm_connections[conversation_key]:
                del self.active_dm_connections[conversation_key]

    async def broadcast_to_dm(self, user_id_1: str, user_id_2: str, message: dict):
        """Broadcast a message to a DM conversation."""
        conversation_key = self.get_dm_conversation_key(user_id_1, user_id_2)
        if conversation_key in self.active_dm_connections:
            for connection in self.active_dm_connections[conversation_key]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error sending DM: {e}")

    # ============ TYPING INDICATORS ============

    async def set_typing(self, channel_id: str, user_id: str):
        """Mark user as typing in a channel."""
        if channel_id not in self.typing_users:
            self.typing_users[channel_id] = set()
        self.typing_users[channel_id].add(user_id)

    async def stop_typing(self, channel_id: str, user_id: str):
        """Mark user as stopped typing."""
        if channel_id in self.typing_users:
            self.typing_users[channel_id].discard(user_id)

    async def get_typing_users(self, channel_id: str) -> List[str]:
        """Get list of users currently typing."""
        if channel_id in self.typing_users:
            return list(self.typing_users[channel_id])
        return []


# Global instance
manager = WebSocketManager()
