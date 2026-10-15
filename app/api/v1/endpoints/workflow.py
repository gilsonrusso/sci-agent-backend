from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from uuid import UUID
from sqlmodel import select

from app.api import deps
from app.schemas.workflow import AdvanceStageRequest, RevertStageRequest
from app.core.workflow import Role, TransitionError
from app.services import workflow_service
from app.services.workflow_service import ArticleNotFoundException
from app.models.project import Project
from app.infrastructure.websocket.manager import workflow_ws_manager

router = APIRouter()


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
    db: deps.SessionDep,
    current_user: deps.CurrentUser = None,
):
    """
    Advances an article to the next stage if authorized by the workflow engine.
    """
    try:
        # In a real app we'd fetch the user role for this specific project here
        # request.user_role would be determined securely on the backend, not trusted from front
        workflow_service.advance_article_stage(
            session=db,
            article_id=article_id,
            user_id=request.user_id,
            user_role=request.user_role,
        )
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
    db: deps.SessionDep,
    current_user: deps.CurrentUser = None,
):
    """
    Returns an article to a previous stage.
    """
    try:
        workflow_service.revert_article_stage(
            session=db,
            article_id=article_id,
            user_id=request.user_id,
            user_role=request.user_role,
            target_stage_str=request.target_stage,
            reason=request.reason,
        )
        return {"status": "success", "message": "Article reverted successfully"}
    except ArticleNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TransitionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
