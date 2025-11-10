from typing import Dict, List
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # Store connections by channel_id
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel_id: str):
        """Accept a websocket connection and add to channel."""
        await websocket.accept()
        if channel_id not in self.active_connections:
            self.active_connections[channel_id] = []
        self.active_connections[channel_id].append(websocket)
        print(f"Client connected to channel {channel_id}")

    def disconnect(self, websocket: WebSocket, channel_id: str):
        """Remove a websocket connection from channel."""
        if channel_id in self.active_connections:
            self.active_connections[channel_id].remove(websocket)
            if len(self.active_connections[channel_id]) == 0:
                del self.active_connections[channel_id]
        print(f"Client disconnected from channel {channel_id}")

    async def broadcast_to_channel(self, channel_id: str, data: dict):
        """Send message to all clients in a channel."""
        if channel_id not in self.active_connections:
            return
        
        for connection in self.active_connections[channel_id]:
            try:
                await connection.send_json(data)
            except Exception as e:
                print(f"Error broadcasting to client: {e}")

    async def send_personal_message(self, websocket: WebSocket, data: dict):
        """Send message to a specific client."""
        try:
            await websocket.send_json(data)
        except Exception as e:
            print(f"Error sending personal message: {e}")


manager = ConnectionManager()
