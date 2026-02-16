import logging
from typing import List
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Response
from app.models.project import Project
from app.api.deps import SessionDep
from app.services.compiler import compiler_service
from app.schemas.compiler import CompileRequest

router = APIRouter()


# Simple Connection Manager for WebSocket
class ConnectionManager:
    def __init__(self):
        # Store active connections: project_id -> List[WebSocket]
        self.active_connections: dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, project_id: str):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id] = [
            c
            for c in self.active_connections[project_id]
            if c.client_state.name != "DISCONNECTED"
        ]
        self.active_connections[project_id].append(websocket)

    def disconnect(self, websocket: WebSocket, project_id: str):
        if project_id in self.active_connections:
            if websocket in self.active_connections[project_id]:
                self.active_connections[project_id].remove(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]

    async def broadcast(self, message: bytes, project_id: str, sender: WebSocket):
        if project_id in self.active_connections:
            # Clean up disconnected
            self.active_connections[project_id] = [
                c
                for c in self.active_connections[project_id]
                if c.client_state.name != "DISCONNECTED"
            ]

            for connection in self.active_connections[project_id]:
                if connection != sender:
                    try:
                        await connection.send_bytes(message)
                    except Exception as e:
                        print(f"Error broadcasting to client: {e}")


manager = ConnectionManager()


@router.websocket("/{project_id}/ws")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    await manager.connect(websocket, project_id)
    try:
        while True:
            data = await websocket.receive_bytes()
            await manager.broadcast(data, project_id, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, project_id)


@router.post("/{project_id}/compile")
async def compile_project(
    project_id: uuid.UUID,
    request: CompileRequest,
    session: SessionDep,
):
    """
    Compile the project's LaTeX content into a PDF.
    """
    try:
        pdf_bytes = await compiler_service.compile_project(
            str(project_id), request.content
        )
        return Response(content=pdf_bytes, media_type="application/pdf")
    except Exception as e:
        print(f"Compilation error: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
