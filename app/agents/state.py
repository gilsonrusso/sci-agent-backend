from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class Article(TypedDict):
    title: str
    authors: List[str]
    year: int
    url: str
    snippet: str
    citation_count: int


class OnboardingState(TypedDict):
    # Context
    user_id: Optional[str]

    # Chat History
    messages: Annotated[List[BaseMessage], add_messages]

    # Project Metadata (Extracted)
    topic: Optional[str]
    refined_topic: Optional[str]
    deadline: Optional[str]

    # Search Data
    suggested_articles: Optional[List[Article]]
    selected_articles: Optional[List[Article]]

    # Final Plan
    roadmap: List[Dict[str, Any]]  # List of tasks
    project_title: Optional[str]
    abstract: Optional[str]  # Adicionado para facilitar extração
    project_structure: Optional[
        Dict[str, str]
    ]  # e.g. {"abstract": "...", "introduction": "..."}

    # UI/Progress state
    todos: Optional[List[Dict[str, Any]]]

    # Control Flags
    current_step: str  # 'clarify', 'search', 'roadmap', 'confirm'
