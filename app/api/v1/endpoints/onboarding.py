import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.agents.sub_agents.supervisor import get_onboarding_supervisor
from app.api.deps import CurrentUser, SessionDep
from app.services import project_service, onboarding_session_service
from app.infrastructure.ai.checkpointer import get_checkpointer
from app.infrastructure.ai.onboarding_service import OnboardingService
from app.models.project import Project
from fastapi import APIRouter, Depends, HTTPException
from langgraph.types import Command
from pydantic import BaseModel
from fastapi.responses import StreamingResponse

router = APIRouter()

# Global Service
onboarding_service = OnboardingService()


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
    Create a project from onboarding data.
    """
    try:
        return project_service.create_project_from_onboarding(
            session=session,
            user_id=current_user.id,
            title=data.project_title or data.topic,
            abstract=(
                data.project_structure.get("abstract", "") if data.project_structure else ""
            ),
            tasks=data.roadmap,
            articles=data.selected_articles,
            topic=data.topic,
        )
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
                message=result.get("message") or "[AÇÃO REQUERIDA]",
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
    text: Any = ""
    interrupts: Any = None
    structured_data: Optional[Dict[str, Any]] = None


@router.post("/chat/invoke")
async def chat_onboarding_invoke(
    request: ChatRequest, current_user: CurrentUser, session: SessionDep
):
    """
    Streaming endpoint for Onboarding Multi-Agent via OnboardingService.
    Also tracks the history header in OnboardingSession Table.
    """
    # Create or update Session Header
    conv_id = uuid.UUID(request.conversation_id)
    existing_session = onboarding_session_service.get_onboarding_session(session, conv_id)

    if not existing_session:
        title = (
            request.message[:30] + "..."
            if len(request.message) > 30
            else request.message
        )
        onboarding_session_service.create_onboarding_session(session, current_user.id, conv_id, title)
    else:
        onboarding_session_service.update_onboarding_session_timestamp(session, conv_id)

    return StreamingResponse(
        onboarding_service.chat_stream(
            message=request.message,
            conversation_id=request.conversation_id,
            context=request.project_context,
            search_source=request.search_source,
            user_id=str(current_user.id),
        ),
        media_type="application/x-ndjson",
    )


@router.post("/chat/reply_interrupt")
async def chat_onboarding_reply_interrupt(
    request: ChatResumeRequest, current_user: CurrentUser
):
    """
    Endpoint responsible to unlock graph after an Interrupt via StreamingResponse.
    """
    return StreamingResponse(
        onboarding_service.chat_stream(
            message=None,
            conversation_id=request.conversation_id,
            search_source=request.search_source,
            user_id=str(current_user.id),
            is_resume=True,
            resume_data=request.decision,
            interrupt_id=request.interrupt_id
        ),
        media_type="application/x-ndjson",
    )


class SessionResponse(BaseModel):
    id: uuid.UUID
    title: str
    updated_at: datetime


@router.get("/chat/sessions", response_model=List[SessionResponse])
def get_user_sessions(current_user: CurrentUser, session: SessionDep):
    """
    List all chat sessions for the Gemini Sidebar.
    """
    sessions = onboarding_session_service.get_all_sessions_for_user(session, current_user.id)
    return [
        SessionResponse(id=s.id, title=s.title, updated_at=s.updated_at)
        for s in sessions
    ]


@router.delete("/chat/sessions/{conversation_id}")
def delete_user_session(
    conversation_id: str, current_user: CurrentUser, session: SessionDep
):
    """
    Deletes a specific chat session header.
    """
    conv_id = uuid.UUID(conversation_id)
    existing_session = onboarding_session_service.get_onboarding_session(session, conv_id)

    if not existing_session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    if existing_session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Não autorizado")

    onboarding_session_service.delete_onboarding_session(session, conv_id)
    return {"status": "success"}


@router.get("/chat/sessions/{conversation_id}/history")
async def get_session_history(conversation_id: str, current_user: CurrentUser):
    """
    Get the state history of a specific conversation from PostgresSaver checkpointer.
    Returns messages reconstructed for frontend.
    """
    conv_id = uuid.UUID(conversation_id)
    config = {"configurable": {"thread_id": str(conv_id)}}

    msgs = []

    async with get_checkpointer() as checkpointer:
        graph = get_onboarding_supervisor(checkpointer=checkpointer)
        state_history = [s async for s in graph.aget_state_history(config)]

        # In aget_state_history, index 0 is the most recent state.
        # So we just take index 0, check the messages there.
        if (
            state_history
            and state_history[0].values
            and "messages" in state_history[0].values
        ):
            raw_msgs = state_history[0].values["messages"]
            for i, m in enumerate(raw_msgs):
                if m.type == "human":
                    msgs.append(
                        {
                            "id": getattr(m, "id", str(uuid.uuid4())),
                            "type": "human",
                            "content": m.content,
                        }
                    )
                elif m.type == "ai":
                    if not m.content and not getattr(m, "tool_calls", None):
                        continue  # Tool call internals without content

                    # Try to retrieve agent_name
                    agent_name = getattr(m, "name", "Supervisor") or "Supervisor"
                    friendly_name = onboarding_service.AGENT_NAME_MAPPING.get(
                        agent_name, agent_name
                    )

                    content = ""
                    if isinstance(m.content, list):
                        text_parts = []
                        for block in m.content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text_parts.append(block.get("text", ""))
                            elif isinstance(block, str):
                                text_parts.append(block)
                        content = "".join(text_parts).strip()
                    else:
                        content = str(m.content).strip()

                    # Reconstruct tool calls if any (for extraction)
                    structured_data = None

                    # Logic: only extract articles if this specific message has the tool calls
                    # or is the content of the search turn.
                    # For simplify, we check if this message is the latest in history
                    # OR if it was the one that called suggest_articles.

                    msg_data = {
                        "id": getattr(m, "id", str(uuid.uuid4())),
                        "type": "ai",
                        "agent_name": friendly_name,
                        "content": content,
                        "structured_data": None,
                    }

                    # Check for articles/roadmap in THIS message specifically
                    if hasattr(m, "tool_calls") and m.tool_calls:
                        for tc in m.tool_calls:
                            if tc["name"] == "suggest_articles_to_user":
                                articles = tc["args"].get("articles", [])
                                if articles:
                                    msg_data["structured_data"] = {
                                        "suggested_articles": articles
                                    }
                            elif tc["name"] == "create_project_and_roadmap":
                                msg_data["structured_data"] = {
                                    "roadmap": tc["args"].get("tasks", []),
                                    "project_title": tc["args"].get("title", ""),
                                    "abstract": tc["args"].get("abstract", ""),
                                }

                    # Only add if there is content or structured data
                    if content or msg_data["structured_data"]:
                        msgs.append(msg_data)

            # Special Case: Attach 'todos' ONLY to the very last message in the history
            if msgs and msgs[-1]["type"] == "ai":
                latest_state = state_history[0].values
                if latest_state.get("todos"):
                    if not msgs[-1]["structured_data"]:
                        msgs[-1]["structured_data"] = {}
                    msgs[-1]["structured_data"]["todos"] = latest_state["todos"]

        # Check for active interrupts to persist UI state after reload
        active_interrupt = None
        if (
            state_history
            and state_history[0].tasks
            and state_history[0].tasks[0].interrupts
        ):
            task = state_history[0].tasks[0]
            active_interrupt = {"id": task.id, "interrupts": task.interrupts[0].value}

    return {"messages": msgs, "active_interrupt": active_interrupt}
