from typing import TypedDict, List, Optional, Dict, Any
from langchain_core.messages import BaseMessage


class Article(TypedDict):
    title: str
    authors: List[str]
    year: int
    url: str
    snippet: str
    citation_count: int


from langgraph.graph.message import add_messages
from typing import Annotated


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
