import logging
from typing import List
import uuid
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Response
from app.models.project import Project
from app.api.deps import SessionDep
from app.services.compiler import compiler_service
from app.services.collaboration import collaboration_service
from app.schemas.compiler import CompileRequest


class FastAPIwebsocketAdapter:
    def __init__(self, websocket: WebSocket):
        self._websocket = websocket

    async def send(self, message: bytes):
        await self._websocket.send_bytes(message)

    async def recv(self) -> bytes:
        data = await self._websocket.receive_bytes()
        return data

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return await self.recv()
        except WebSocketDisconnect:
            raise StopAsyncIteration
        except Exception as e:
            raise StopAsyncIteration

    @property
    def path(self) -> str:
        return self._websocket.url.path


router = APIRouter()


@router.websocket("/ws/{project_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    project_id: str,
):
    """
    WebSocket endpoint for Yjs collaboration.
    URL: /api/v1/editor/ws/{project_id}
    The {project_id} here captures the 'room name' sent by y-websocket.
    """
    try:
        room = collaboration_service.get_room(project_id)
    except Exception as e:
        await websocket.close(code=1011)  # internal error
        return

    await websocket.accept()
    logging.info(f"WebSocket accepted for project/room {project_id}")

    # Wait for room to be ready (loaded from DB)
    wait_count = 0
    while not room.ready:
        if wait_count % 10 == 0:
            logging.info(f"Waiting for room {project_id} to be ready... ({wait_count})")
        await asyncio.sleep(0.1)
        wait_count += 1

    logging.info(f"Room {project_id} is ready. Starting adapter.")
    adapter = FastAPIwebsocketAdapter(websocket)
    try:
        await room.serve(adapter)
    except Exception as e:
        # Check if it's a disconnect
        # ypy-websocket might raise or just return
        pass


@router.post("/{project_id}/compile")
async def compile_project(
    project_id: uuid.UUID,
    # request: CompileRequest, # Content from client is ignored or optional
    session: SessionDep,
):
    """
    Compile the project's LaTeX content into a PDF.
    Uses Server-Side State (YDoc or DB).
    """
    project_id_str = str(project_id)
    content = ""

    # 1. Check active room
    room = collaboration_service.rooms.get(project_id_str)
    if room and room.ready:
        content = str(room.ydoc.get_text("codemirror"))
        logging.info(f"Compiling from Active YRoom: {project_id_str}")
    else:
        # 2. Check DB
        project = session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        content = project.content or ""
        logging.info(f"Compiling from DB: {project_id_str}")

    try:
        pdf_bytes = await compiler_service.compile_project(project_id_str, content)
        return Response(content=pdf_bytes, media_type="application/pdf")
    except Exception as e:
        print(f"Compilation error: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
