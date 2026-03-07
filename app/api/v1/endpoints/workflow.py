from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.api import deps
from app.application.dto.workflow import AdvanceStageRequest, RevertStageRequest
from app.application.use_cases.advance_article_stage import (
    AdvanceArticleStageUseCase,
    ArticleNotFoundException,
)
from app.application.use_cases.revert_article_stage import RevertArticleStageUseCase
from app.infrastructure.repositories.sql_article_repository import SQLArticleRepository
from app.infrastructure.events.simple_event_bus import event_bus
from app.domain.workflow.state_machine import TransitionError
from app.models.user import User
from app.models.project_member import ProjectRole
from app.domain.workflow.types import Role

router = APIRouter()


def get_advance_use_case(
    db: deps.SessionDep,
) -> AdvanceArticleStageUseCase:
    repo = SQLArticleRepository(db)
    return AdvanceArticleStageUseCase(article_repository=repo, event_bus=event_bus)


def get_revert_use_case(
    db: deps.SessionDep,
) -> RevertArticleStageUseCase:
    repo = SQLArticleRepository(db)
    return RevertArticleStageUseCase(article_repository=repo, event_bus=event_bus)


from sqlmodel import select
from app.models.project import Project


@router.get("/articles/board")
def get_board_articles(
    db: deps.SessionDep,
    current_user: deps.CurrentUser = None,
):
    """
    Fetches all articles for the Kanban board.
    In a real app, this would filter by the user's role and visibility.
    """
    projects = db.exec(select(Project)).all()

    # Map to frontend Article interface
    board_articles = []
    for p in projects:
        board_articles.append(
            {
                "id": str(p.id),
                "title": p.title,
                "macroStatus": p.stage.value if hasattr(p.stage, "value") else p.stage,
                "subSections": [],  # Mocked for now
                "deadline": p.deadline.isoformat() if p.deadline else None,
                "createdAt": p.created_at.isoformat() if p.created_at else None,
                "updatedAt": p.updated_at.isoformat() if p.updated_at else None,
                "authors": [
                    {"id": str(p.owner_id), "name": "Author"}
                ],  # Would come from relations
                "progress": 20,  # Mocked
            }
        )

    return board_articles


@router.post("/{article_id}/advance")
def advance_article_stage(
    article_id: UUID,
    request: AdvanceStageRequest,
    use_case: AdvanceArticleStageUseCase = Depends(get_advance_use_case),
    current_user: deps.CurrentUser = None,
):
    """
    Advances an article to the next stage if authorized by the workflow engine.
    """
    try:
        # In a real app we'd fetch the user role for this specific project here
        # request.user_role would be determined securely on the backend, not trusted from front
        use_case.execute(article_id, request)
        return {"status": "success", "message": "Article advanced successfully"}
    except ArticleNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TransitionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{article_id}/revert")
def revert_article_stage(
    article_id: UUID,
    request: RevertStageRequest,
    use_case: RevertArticleStageUseCase = Depends(get_revert_use_case),
    current_user: deps.CurrentUser = None,
):
    """
    Returns an article to a previous stage.
    """
    try:
        use_case.execute(article_id, request)
        return {"status": "success", "message": "Article reverted successfully"}
    except ArticleNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TransitionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


from fastapi import WebSocket, WebSocketDisconnect
from app.infrastructure.websocket.manager import workflow_ws_manager


@router.websocket("/ws/{article_id}")
async def workflow_websocket_endpoint(websocket: WebSocket, article_id: str):
    """
    Subscribes a client to receive real-time transition events for a specific article.
    """
    await workflow_ws_manager.connect(websocket, article_id)
    try:
        while True:
            # We don't expect messages from the client in this specific connection,
            # just keeping the connection alive.
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        workflow_ws_manager.disconnect(websocket, article_id)
