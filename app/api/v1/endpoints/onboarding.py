import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.agents.sub_agents.supervisor import get_onboarding_supervisor
from app.api.deps import CurrentUser, SessionDep
from app.application.use_cases.onboarding.create_project_use_case import (
    CreateProjectFromOnboardingUseCase,
)
from app.domain.onboarding.entities import OnboardingProposta, OnboardingTask
from app.infrastructure.ai.checkpointer import get_checkpointer
from app.infrastructure.ai.onboarding_service import OnboardingService
from app.infrastructure.events.event_bus import LocalEventBus
from app.infrastructure.repositories.sql_onboarding_session_repository import (
    SQLOnboardingSessionRepository,
)
from app.infrastructure.repositories.sql_project_repository import SQLProjectRepository
from app.models.project import Project
from fastapi import APIRouter, Depends, HTTPException
from langgraph.types import Command
from pydantic import BaseModel

router = APIRouter()

# Global Service
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


@router.post("/chat/invoke", response_model=ChatSyncResponse)
async def chat_onboarding_invoke(
    request: ChatRequest, current_user: CurrentUser, session: SessionDep
):
    """
    Synchronous endpoint for Onboarding Multi-Agent via OnboardingService.
    Also tracks the history header in OnboardingSession Table.
    """
    # Create or update Session Header
    conv_id = uuid.UUID(request.conversation_id)
    session_repo = SQLOnboardingSessionRepository(session)
    existing_session = session_repo.get_by_id(conv_id)

    if not existing_session:
        title = (
            request.message[:30] + "..."
            if len(request.message) > 30
            else request.message
        )
        session_repo.create(current_user.id, conv_id, title)
    else:
        session_repo.update_timestamp(conv_id)

    try:
        result = await onboarding_service.chat(
            message=request.message,
            conversation_id=request.conversation_id,
            context=request.project_context,
            search_source=request.search_source,
            user_id=str(current_user.id),
        )

        if result["type"] == "interrupt":
            response = ChatSyncResponse(
                id=result["id"],
                type="interrupt",
                agent_name=result["agent_name"],
                text=result.get("message") or "[AÇÃO REQUERIDA]",
                interrupts=result["interrupts"],
                structured_data=result.get("structured_data"),
            )
        else:
            response = ChatSyncResponse(
                id=str(uuid.uuid4()),
                type="message",
                agent_name=result["agent_name"],
                text=result["message"],
                structured_data=result.get("structured_data"),
            )

        print(
            f"DEBUG: Final Response to Frontend: Type={response.type}, HasStructuredData={response.structured_data is not None}"
        )
        if response.structured_data:
            print(
                f"DEBUG: Structured Data Keys: {list(response.structured_data.keys())}"
            )

        return response

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/reply_interrupt", response_model=ChatSyncResponse)
async def chat_onboarding_reply_interrupt(
    request: ChatResumeRequest, current_user: CurrentUser
):
    """
    Endpoint responsible to unlock graph after an Interrupt, with Race Condition checks.
    """
    config = {
        "configurable": {
            "thread_id": request.conversation_id,
            "search_source": request.search_source,
        }
    }
    if onboarding_service.langfuse_handler:
        config["callbacks"] = [onboarding_service.langfuse_handler]

    # Use context manager
    async with get_checkpointer() as checkpointer:
        graph = get_onboarding_supervisor(checkpointer=checkpointer)

        # Verify we are replying to the CORRECT interrupt
        state = await graph.aget_state(config)

        # 1. Race condition protection: Check if the graph is actually paused and matches the interrupt_id
        if not state.tasks or not state.tasks[0].interrupts:
            raise HTTPException(
                status_code=400,
                detail="Grafo não está aguardando interrupções. Ele já pode ter sido resumido.",
            )

        current_interrupt_id = state.tasks[0].id
        if request.interrupt_id != current_interrupt_id:
            raise HTTPException(
                status_code=400,
                detail=f"O interrupt_id fornecido ({request.interrupt_id}) não corresponde ao estado atual do grafo ({current_interrupt_id}). Evitando race condition.",
            )

        num_hanging = len(state.tasks[0].interrupts)

        # Decisions vector
        if num_hanging > 1:
            decisions = [request.decision] * num_hanging
            resume_command = Command(resume={"decisions": decisions})
        else:
            resume_command = Command(resume={"decisions": [request.decision]})

        try:
            result = await graph.ainvoke(resume_command, config=config)

            # Determine if we are still interrupted
            state = await graph.aget_state(config)

            is_interrupted = (
                len(state.next) > 0
                and len(state.tasks) > 0
                and hasattr(state.tasks[0], "interrupts")
                and state.tasks[0].interrupts
            )

            # Extract textual information using centralized logic
            msgs_to_parse = (
                result.get("messages", []) if isinstance(result, dict) else []
            )
            if not msgs_to_parse:
                msgs_to_parse = state.values.get("messages", [])

            extracted = onboarding_service.extract_messages(msgs_to_parse)

            # Extract structured data dynamically using our new method
            structured_data = await onboarding_service.extract_structured_data(
                state.values, result if isinstance(result, dict) else {}
            )

            if is_interrupted:
                response = ChatSyncResponse(
                    id=state.tasks[0].id,
                    type="interrupt",
                    agent_name=extracted["agent_name"],
                    text=extracted["text"] or "[AÇÃO REQUERIDA]",
                    interrupts=state.tasks[0].interrupts[0].value,
                    structured_data=structured_data if structured_data else None,
                )
            else:
                response = ChatSyncResponse(
                    id=str(uuid.uuid4()),
                    type="message",
                    agent_name=extracted["agent_name"],
                    text=extracted["text"],
                    structured_data=structured_data if structured_data else None,
                )

            print(
                f"DEBUG REPY: Final Response: Type={response.type}, HasStructuredData={response.structured_data is not None}"
            )
            if response.structured_data:
                print(
                    f"DEBUG REPLY: Structured Data Keys: {list(response.structured_data.keys())}"
                )

            return response

        except Exception as e:
            print(f"ERROR in chat_onboarding_reply_interrupt: {e}")
            import traceback

            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))


class SessionResponse(BaseModel):
    id: uuid.UUID
    title: str
    updated_at: datetime


@router.get("/chat/sessions", response_model=List[SessionResponse])
def get_user_sessions(current_user: CurrentUser, session: SessionDep):
    """
    List all chat sessions for the Gemini Sidebar.
    """
    repo = SQLOnboardingSessionRepository(session)
    sessions = repo.get_all_for_user(current_user.id)
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
    repo = SQLOnboardingSessionRepository(session)
    conv_id = uuid.UUID(conversation_id)
    existing_session = repo.get_by_id(conv_id)

    if not existing_session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    if existing_session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Não autorizado")

    repo.delete(conv_id)
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
