from fastapi import WebSocket
from typing import Dict, List, Any
import json
import asyncio


class WorkflowConnectionManager:
    def __init__(self):
        # Maps article_id (stringified UUID) to a list of active websocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, article_id: str):
        await websocket.accept()
        if article_id not in self.active_connections:
            self.active_connections[article_id] = []
        self.active_connections[article_id].append(websocket)

    def disconnect(self, websocket: WebSocket, article_id: str):
        if article_id in self.active_connections:
            self.active_connections[article_id].remove(websocket)
            if not self.active_connections[article_id]:
                del self.active_connections[article_id]

    async def broadcast_to_article(self, article_id: str, message: dict):
        """Send a message to all clients viewing this specific article"""
        if article_id in self.active_connections:
            # Create tasks for concurrent sending
            tasks = []
            for connection in self.active_connections[article_id]:
                tasks.append(connection.send_text(json.dumps(message)))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_global(self, message: dict):
        """Send a message to all connected clients (e.g. for the Mentor Board)"""
        tasks = []
        for connections in self.active_connections.values():
            for connection in connections:
                tasks.append(connection.send_text(json.dumps(message)))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


workflow_ws_manager = WorkflowConnectionManager()
