import asyncio
import logging
from typing import Dict, Optional
from uuid import UUID
import y_py as Y
from ypy_websocket.yroom import YRoom
from sqlmodel import Session, select
from app.db.session import engine
from app.models.project import Project

logger = logging.getLogger(__name__)


class CollaborationService:
    def __init__(self):
        self.rooms: Dict[str, YRoom] = {}
        self.save_tasks: Dict[str, asyncio.Task] = {}

    def get_room(self, project_id: str) -> YRoom:
        if project_id not in self.rooms:
            logger.info(f"Creating new YRoom for project {project_id}")
            room = YRoom(ready=False)
            self.rooms[project_id] = room

            # Start the room loop in background
            asyncio.create_task(self._run_room(room, project_id))

            # Load content
            asyncio.create_task(self._load_room_from_db(project_id))
        return self.rooms[project_id]

    async def _run_room(self, room: YRoom, project_id: str):
        try:
            await room.start()
        except Exception as e:
            logger.error(f"YRoom {project_id} crashed: {e}")
            # If room crashes, remove it so it can be recreated
            self.rooms.pop(project_id, None)

    async def _load_room_from_db(self, project_id: str):
        room = self.rooms[project_id]

        try:
            # Run blocking DB op in thread
            initial_content = await asyncio.to_thread(
                self._fetch_content_sync, project_id
            )

            if initial_content:
                # Initialize YText with content if document is empty
                # We do this in a transaction
                def init_transaction(txn):
                    ytext = txn.get_text("codemirror")
                    if len(ytext) == 0:
                        ytext.extend(txn, initial_content)

                room.ydoc.transact(init_transaction)
                logger.info(
                    f"Loaded content for project {project_id} from DB into YDoc"
                )
        except Exception as e:
            logger.error(f"Error loading project {project_id} from DB: {e}")

        # Mark room as ready for connections
        room.ready = True

        # Setup save observer
        ytext = room.ydoc.get_text("codemirror")
        ytext.observe(lambda event: self._schedule_save(project_id))

    def _schedule_save(self, project_id: str):
        # Debounce logic: Cancel existing task if pending
        if project_id in self.save_tasks:
            self.save_tasks[project_id].cancel()

        # Schedule new save
        self.save_tasks[project_id] = asyncio.create_task(
            self._debounce_save(project_id)
        )

    async def _debounce_save(self, project_id: str):
        try:
            await asyncio.sleep(2.0)  # 2s debounce
            await self._save_room_to_db(project_id)
        except asyncio.CancelledError:
            pass
        finally:
            self.save_tasks.pop(project_id, None)

    async def _save_room_to_db(self, project_id: str):
        room = self.rooms.get(project_id)
        if not room:
            return

        content = str(room.ydoc.get_text("codemirror"))
        await asyncio.to_thread(self._save_content_sync, project_id, content)

    def _fetch_content_sync(self, project_id: str) -> Optional[str]:
        with Session(engine) as session:
            project = session.get(Project, UUID(project_id))
            return project.content if project else None

    def _save_content_sync(self, project_id: str, content: str):
        try:
            with Session(engine) as session:
                project = session.get(Project, UUID(project_id))
                if project:
                    project.content = content
                    session.add(project)
                    session.commit()
                    logger.info(f"Saved project {project_id} content to DB")
        except Exception as e:
            logger.error(f"Failed to save project {project_id}: {e}")


collaboration_service = CollaborationService()
