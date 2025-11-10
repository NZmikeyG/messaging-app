from typing import List, Dict, Set
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.active_channel_connections: Dict[str, List[WebSocket]] = {}
        self.active_dm_connections: Dict[str, List[WebSocket]] = {}
        self.typing_users: Dict[str, Set[str]] = {}
        logger.info("WebSocketManager initialized")

    # ============ CHANNEL WEBSOCKETS ============

    async def connect_to_channel(self, channel_id: str, websocket: WebSocket, user_id: str):
        """Add a connection to a channel."""
        try:
            await websocket.accept()
            if channel_id not in self.active_channel_connections:
                self.active_channel_connections[channel_id] = []
            self.active_channel_connections[channel_id].append(websocket)
            logger.info(f"User {user_id} connected to channel {channel_id}. Active connections: {len(self.active_channel_connections[channel_id])}")
        except Exception as e:
            logger.error(f"Error connecting user {user_id} to channel {channel_id}: {e}", exc_info=True)
            raise

    def disconnect_from_channel(self, channel_id: str, websocket: WebSocket, user_id: str):
        """Remove a connection from a channel."""
        try:
            if channel_id in self.active_channel_connections:
                self.active_channel_connections[channel_id].remove(websocket)
                logger.info(f"User {user_id} disconnected from channel {channel_id}")
                if not self.active_channel_connections[channel_id]:
                    del self.active_channel_connections[channel_id]
        except Exception as e:
            logger.error(f"Error disconnecting user {user_id} from channel {channel_id}: {e}", exc_info=True)

    async def broadcast_to_channel(self, channel_id: str, message: dict, sender_id: str = None):
        """Broadcast a message to all users in a channel."""
        if channel_id in self.active_channel_connections:
            failed_connections = []
            for connection in self.active_channel_connections[channel_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send message in channel {channel_id}: {e}")
                    failed_connections.append(connection)
            
            # Remove failed connections
            for conn in failed_connections:
                try:
                    self.active_channel_connections[channel_id].remove(conn)
                except:
                    pass
            
            logger.debug(f"Broadcast to {len(self.active_channel_connections[channel_id])} users in channel {channel_id}")

    # ============ DIRECT MESSAGE WEBSOCKETS ============

    def get_dm_conversation_key(self, user_id_1: str, user_id_2: str) -> str:
        """Generate a unique key for a DM conversation."""
        ids = sorted([user_id_1, user_id_2])
        return f"dm_{ids[0]}_{ids[1]}"

    async def connect_to_dm(self, user_id_1: str, user_id_2: str, websocket: WebSocket):
        """Add a connection to a DM conversation."""
        try:
            await websocket.accept()
            conversation_key = self.get_dm_conversation_key(user_id_1, user_id_2)
            if conversation_key not in self.active_dm_connections:
                self.active_dm_connections[conversation_key] = []
            self.active_dm_connections[conversation_key].append(websocket)
            logger.info(f"User {user_id_1} connected to DM with {user_id_2}. Active connections: {len(self.active_dm_connections[conversation_key])}")
        except Exception as e:
            logger.error(f"Error connecting to DM between {user_id_1} and {user_id_2}: {e}", exc_info=True)
            raise

    def disconnect_from_dm(self, user_id_1: str, user_id_2: str, websocket: WebSocket):
        """Remove a connection from a DM conversation."""
        try:
            conversation_key = self.get_dm_conversation_key(user_id_1, user_id_2)
            if conversation_key in self.active_dm_connections:
                self.active_dm_connections[conversation_key].remove(websocket)
                logger.info(f"User {user_id_1} disconnected from DM with {user_id_2}")
                if not self.active_dm_connections[conversation_key]:
                    del self.active_dm_connections[conversation_key]
        except Exception as e:
            logger.error(f"Error disconnecting from DM between {user_id_1} and {user_id_2}: {e}", exc_info=True)

    async def broadcast_to_dm(self, user_id_1: str, user_id_2: str, message: dict):
        """Broadcast a message to a DM conversation."""
        conversation_key = self.get_dm_conversation_key(user_id_1, user_id_2)
        if conversation_key in self.active_dm_connections:
            failed_connections = []
            for connection in self.active_dm_connections[conversation_key]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send DM in conversation {conversation_key}: {e}")
                    failed_connections.append(connection)
            
            for conn in failed_connections:
                try:
                    self.active_dm_connections[conversation_key].remove(conn)
                except:
                    pass

    # ============ TYPING INDICATORS ============

    async def set_typing(self, channel_id: str, user_id: str):
        """Mark user as typing in a channel."""
        if channel_id not in self.typing_users:
            self.typing_users[channel_id] = set()
        self.typing_users[channel_id].add(user_id)
        logger.debug(f"User {user_id} is typing in channel {channel_id}")

    async def stop_typing(self, channel_id: str, user_id: str):
        """Mark user as stopped typing."""
        if channel_id in self.typing_users:
            self.typing_users[channel_id].discard(user_id)
            logger.debug(f"User {user_id} stopped typing in channel {channel_id}")

    async def get_typing_users(self, channel_id: str) -> List[str]:
        """Get list of users currently typing."""
        if channel_id in self.typing_users:
            return list(self.typing_users[channel_id])
        return []


# Global instance
manager = WebSocketManager()
