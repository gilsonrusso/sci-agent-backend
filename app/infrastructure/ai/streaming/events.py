from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class StreamEventBase(BaseModel):
    type: str

    def to_stream_chunk(self) -> str:
        """Helper to serialize as NDJSON for HTTP streaming."""
        return self.model_dump_json(exclude_none=True) + "\n"


class TokenEvent(StreamEventBase):
    """Fired when an Agent is speaking (Yields string chunks)."""
    type: Literal["token"] = "token"
    content: str
    agent_name: str



class AgentSwitchEvent(StreamEventBase):
    """Fired when LangGraph transitions to a new Agent."""
    type: Literal["agent"] = "agent"
    name: str


class StateUpdateEvent(StreamEventBase):
    """Fired when important structured data is committed to the Graph State."""
    type: Literal["state"] = "state"
    data: Dict[str, Any]


class InterruptEvent(StreamEventBase):
    """Fired when the Graph is paused waiting for a Human In The Loop."""
    type: Literal["interrupt"] = "interrupt"
    id: str  # The Task ID to resume
    action: str  # e.g., 'create_project_and_roadmap', 'suggest_articles_to_user'
    data: Dict[str, Any]


class ErrorEvent(StreamEventBase):
    """Fired when the execution catches an unhandled exception."""
    type: Literal["error"] = "error"
    message: str


class EndEvent(StreamEventBase):
    """Fired when the Graph execution successfully finishes."""
    type: Literal["end"] = "end"


StreamEvent = Union[
    TokenEvent, AgentSwitchEvent, StateUpdateEvent, InterruptEvent, ErrorEvent, EndEvent
]
