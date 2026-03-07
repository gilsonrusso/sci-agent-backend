from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import json

from app.api.deps import SessionDep, CurrentUser
from app.models.project import Project
from app.domain.onboarding.entities import OnboardingProposta, OnboardingTask
from app.infrastructure.repositories.sql_project_repository import SQLProjectRepository
from app.infrastructure.ai.onboarding_service import OnboardingService
from app.application.use_cases.onboarding.create_project_use_case import (
    CreateProjectFromOnboardingUseCase,
)
from app.infrastructure.events.event_bus import LocalEventBus
from langgraph.types import Command

router = APIRouter()

# Global Service (Singleton-like for now as it was before)
onboarding_service = OnboardingService()
event_bus = LocalEventBus()


class ProjectCreateFromOnboarding(BaseModel):
    topic: str
    roadmap: List[Dict[str, Any]]
    selected_articles: List[Dict[str, Any]]
    project_title: Optional[str] = None
    project_structure: Optional[Dict[str, str]] = None


@router.post("/create-project", response_model=Project)
def create_project(
    *, session: SessionDep, current_user: CurrentUser, data: ProjectCreateFromOnboarding
) -> Any:
    """
    Create a project from onboarding data using DDD Use Case.
    """
    repo = SQLProjectRepository(session)
    use_case = CreateProjectFromOnboardingUseCase(repo, event_bus)

    # Map DTO to Domain Entity
    roadmap_tasks = [
        OnboardingTask(
            title=t.get("title", ""),
            description=t.get("description", ""),
            due_in_days=t.get("due_in_days", 7),
        )
        for t in data.roadmap
    ]

    proposta = OnboardingProposta(
        topic=data.topic,
        title=data.project_title or data.topic,
        abstract=(
            data.project_structure.get("abstract", "") if data.project_structure else ""
        ),
        roadmap=roadmap_tasks,
        selected_articles=data.selected_articles,
        owner_id=current_user.id,
    )

    try:
        return use_case.execute(proposta)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ChatRequest(BaseModel):
    message: str
    conversation_id: str
    project_context: Optional[Dict[str, Any]] = None
    search_source: Optional[str] = "semantic_scholar"


class ChatResponse(BaseModel):
    message: str
    structured_data: Optional[Dict[str, Any]] = None


@router.post("/chat", response_model=ChatResponse)
async def chat_onboarding(request: ChatRequest):
    """
    Chat with the Onboarding Agent via Infrastructure Service.
    """
    try:
        result = await onboarding_service.chat(
            message=request.message,
            conversation_id=request.conversation_id,
            context=request.project_context,
            search_source=request.search_source,
        )

        if result["type"] == "interrupt":
            return ChatResponse(
                message="[PAUSED] Pending your approval for academic search.",
                structured_data={"interrupt": result},
            )

        return ChatResponse(
            message=result["message"], structured_data=result["structured_data"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ChatResumeRequest(BaseModel):
    conversation_id: str
    interrupt_id: str
    decision: Dict[str, Any]
    search_source: Optional[str] = "semantic_scholar"


class ChatSyncResponse(BaseModel):
    id: str
    type: str  # 'message' ou 'interrupt'
    agent_name: str
    text: str = ""
    interrupts: list = []


@router.post("/chat/invoke", response_model=ChatSyncResponse)
async def chat_onboarding_invoke(request: ChatRequest):
    """
    Synchronous endpoint for Onboarding Multi-Agent via OnboardingService.
    """
    try:
        result = await onboarding_service.chat(
            message=request.message,
            conversation_id=request.conversation_id,
            context=request.project_context,
            search_source=request.search_source,
        )

        if result["type"] == "interrupt":
            return ChatSyncResponse(
                id=result["id"],
                type="interrupt",
                agent_name="system",
                interrupts=result["interrupts"],
            )
        else:
            return ChatSyncResponse(
                id="msg",
                type="message",
                agent_name=result["agent_name"],
                text=result["message"],
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/reply_interrupt", response_model=ChatSyncResponse)
async def chat_onboarding_reply_interrupt(request: ChatResumeRequest):
    """
    Endpoint responsible to unlock graph after an Interrupt.
    """
    config = {
        "configurable": {
            "thread_id": request.conversation_id,
            "search_source": request.search_source,
        }
    }
    if onboarding_service.langfuse_handler:
        config["callbacks"] = [onboarding_service.langfuse_handler]

    resume_command = Command(
        resume={request.interrupt_id: {"decisions": [request.decision]}}
    )

    try:
        result = await onboarding_service.graph.ainvoke(resume_command, config=config)

        state = await onboarding_service.graph.aget_state(config)
        is_interrupted = (
            len(state.next) > 0
            and len(state.tasks) > 0
            and hasattr(state.tasks[0], "interrupts")
            and state.tasks[0].interrupts
        )

        if is_interrupted:
            return ChatSyncResponse(
                id=state.tasks[0].id,
                type="interrupt",
                agent_name="system",
                interrupts=state.tasks[0].interrupts[0].value,
            )
        else:
            last_message = result.get("messages", [])[-1]
            return ChatSyncResponse(
                id="msg",
                type="message",
                agent_name=getattr(last_message, "name", "system") or "system",
                text=(
                    last_message.content
                    if hasattr(last_message, "content")
                    else str(last_message)
                ),
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
