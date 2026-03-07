from typing import Any
import asyncio
from app.infrastructure.events.simple_event_bus import event_bus
from app.domain.workflow.state_machine import (
    ArticleStageAdvancedEvent,
    ArticleReturnedEvent,
)
from app.infrastructure.websocket.manager import workflow_ws_manager


def handle_stage_advanced(event: ArticleStageAdvancedEvent):
    """Observer that listens to Domain Event and triggers WebSocket broadcast"""

    message = {
        "type": "WORKFLOW_STAGE_ADVANCED",
        "payload": {
            "article_id": str(event.article_id),
            "from_stage": str(event.from_stage.value),
            "to_stage": str(event.to_stage.value),
            "user_id": str(event.user_id),
            "occurred_on": event.occurred_on.isoformat(),
        },
    }

    # Needs a new event loop or to run in existing one since event_bus is synchronous here
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(
            workflow_ws_manager.broadcast_to_article(str(event.article_id), message)
        )
        loop.create_task(workflow_ws_manager.broadcast_global(message))
    except RuntimeError:
        # If no loop is running, we just synchronously run it (e.g., in a test)
        asyncio.run(
            workflow_ws_manager.broadcast_to_article(str(event.article_id), message)
        )
        asyncio.run(workflow_ws_manager.broadcast_global(message))


def handle_stage_returned(event: ArticleReturnedEvent):
    """Observer that listens to Domain Event and triggers WebSocket broadcast"""

    message = {
        "type": "WORKFLOW_STAGE_RETURNED",
        "payload": {
            "article_id": str(event.article_id),
            "from_stage": str(event.from_stage.value),
            "to_stage": str(event.to_stage.value),
            "user_id": str(event.user_id),
            "reason": event.reason,
            "occurred_on": event.occurred_on.isoformat(),
        },
    }

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(
            workflow_ws_manager.broadcast_to_article(str(event.article_id), message)
        )
        loop.create_task(workflow_ws_manager.broadcast_global(message))
    except RuntimeError:
        asyncio.run(
            workflow_ws_manager.broadcast_to_article(str(event.article_id), message)
        )
        asyncio.run(workflow_ws_manager.broadcast_global(message))


def register_event_handlers():
    """Registers the functions to listen to the specific events emitting from entities."""
    event_bus.subscribe(ArticleStageAdvancedEvent, handle_stage_advanced)
    event_bus.subscribe(ArticleReturnedEvent, handle_stage_returned)
    print("Workflow domain event handlers registered.")
