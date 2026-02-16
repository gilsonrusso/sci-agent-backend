from typing import Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    project_id: str
    message: str
    context: Optional[str] = None  # Current document content
    chat_history: Optional[list[dict[str, str]]] = (
        None  # [{"role": "user", "content": "..."}, ...]
    )


class ChatResponse(BaseModel):
    response: str
