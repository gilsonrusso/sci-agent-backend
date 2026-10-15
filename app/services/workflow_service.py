import asyncio
import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from sqlmodel import Session

from app.models.project import Project
from app.core.workflow import MacroStage, Role, WorkflowEngine, TransitionError
from app.infrastructure.websocket.manager import workflow_ws_manager


class ArticleNotFoundException(Exception):
    pass


def _broadcast_workflow_event(article_id: str, message: dict):
    """
    Safely schedules the WebSocket broadcast tasks on the running event loop
    or runs them synchronously if no loop is running.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(
            workflow_ws_manager.broadcast_to_article(article_id, message)
        )
        loop.create_task(workflow_ws_manager.broadcast_global(message))
    except RuntimeError:
        # Fallback for synchronous/test environments
        asyncio.run(
            workflow_ws_manager.broadcast_to_article(article_id, message)
        )
        asyncio.run(workflow_ws_manager.broadcast_global(message))


def advance_article_stage(
    session: Session,
    article_id: UUID,
    user_id: UUID,
    user_role: Role,
) -> Project:
    """
    Advances an article (project) to the next stage if allowed by the workflow engine.
    """
    # 1. Retrieve Project
    project = session.get(Project, article_id)
    if not project:
        raise ArticleNotFoundException(f"Article with id {article_id} not found.")

    from_stage = project.stage

    # 2. Get next stage
    next_stage = WorkflowEngine._FORWARD_TRANSITIONS.get(from_stage)
    if not next_stage:
        raise ValueError("Article is at final stage and cannot advance further.")

    # 3. Validate Transition
    WorkflowEngine.validate_transition(from_stage, next_stage, user_role)

    # 4. Apply Stage transition
    project.stage = next_stage
    project.updated_at = datetime.utcnow()

    session.add(project)
    session.commit()
    session.refresh(project)

    # 5. Notify WebSockets directly (without Event Bus)
    message = {
        "type": "WORKFLOW_STAGE_ADVANCED",
        "payload": {
            "article_id": str(article_id),
            "from_stage": str(from_stage.value if hasattr(from_stage, 'value') else from_stage),
            "to_stage": str(next_stage.value if hasattr(next_stage, 'value') else next_stage),
            "user_id": str(user_id),
            "occurred_on": datetime.now(timezone.utc).isoformat(),
        },
    }
    _broadcast_workflow_event(str(article_id), message)

    return project


def revert_article_stage(
    session: Session,
    article_id: UUID,
    user_id: UUID,
    user_role: Role,
    target_stage_str: str,
    reason: Optional[str] = None,
) -> Project:
    """
    Reverts an article (project) to a previous stage if allowed by the workflow engine.
    """
    # 1. Retrieve Project
    project = session.get(Project, article_id)
    if not project:
        raise ArticleNotFoundException(f"Article with id {article_id} not found.")

    from_stage = project.stage

    # 2. Convert and validate target stage enum
    try:
        target_stage = MacroStage(target_stage_str)
    except ValueError:
        raise ValueError(f"Invalid target stage: {target_stage_str}")

    # 3. Validate Reversion
    WorkflowEngine.validate_reversion(from_stage, target_stage, user_role)

    # 4. Apply reversion
    project.stage = target_stage
    project.updated_at = datetime.utcnow()

    session.add(project)
    session.commit()
    session.refresh(project)

    # 5. Notify WebSockets directly (without Event Bus)
    message = {
        "type": "WORKFLOW_STAGE_RETURNED",
        "payload": {
            "article_id": str(article_id),
            "from_stage": str(from_stage.value if hasattr(from_stage, 'value') else from_stage),
            "to_stage": str(target_stage.value if hasattr(target_stage, 'value') else target_stage),
            "user_id": str(user_id),
            "reason": reason,
            "occurred_on": datetime.now(timezone.utc).isoformat(),
        },
    }
    _broadcast_workflow_event(str(article_id), message)

    return project
