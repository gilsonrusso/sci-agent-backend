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
    # Chat History
    messages: Annotated[List[BaseMessage], add_messages]

    # Project Metadata (Extracted)
    topic: Optional[str]
    refined_topic: Optional[str]
    deadline: Optional[str]

    # Search Data
    suggested_articles: List[Article]
    selected_articles: List[Article]

    # Final Plan
    roadmap: List[Dict[str, Any]]  # List of tasks
    project_title: Optional[str]
    project_structure: Optional[
        Dict[str, str]
    ]  # e.g. {"abstract": "...", "introduction": "..."}

    # Control Flags
    current_step: str  # 'clarify', 'search', 'roadmap', 'confirm'
