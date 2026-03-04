from typing import Any
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage

from app.api.deps import CurrentUser
from app.schemas.agent import ChatRequest
from app.agents.writer import writer_agent
import os
from app.core.observability import get_langfuse_handler

langfuse_handler = get_langfuse_handler()

router = APIRouter()


@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: CurrentUser,
) -> Any:
    """
    Chat with the AI Assistant about the project content.
    """
    print(
        f"Chat Request: message='{request.message}' context_len={len(request.context) if request.context else 0}"
    )
    # Convert history
    history = []
    if request.chat_history:
        for msg in request.chat_history:
            if msg["role"] == "user":
                history.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                history.append(AIMessage(content=msg["content"]))

    async def generate():
        config = {}
        if langfuse_handler:
            config["callbacks"] = [langfuse_handler]

        async for chunk in writer_agent.astream(
            {
                "chat_history": history,
                "document_content": request.context or "",
                "input": request.message,
            },
            config=config,
        ):
            yield chunk

    return StreamingResponse(generate(), media_type="text/event-stream")
