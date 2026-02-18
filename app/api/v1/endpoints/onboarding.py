from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from langchain_core.messages import HumanMessage
from app.agents.onboarding import onboarding_graph

from app.api.deps import SessionDep, CurrentUser
from app.models.project import Project
from app.models.project_task import ProjectTask, TaskStatus
from app.models.project_member import ProjectMember, ProjectRole


class ProjectCreateFromOnboarding(BaseModel):
    topic: str
    roadmap: List[Dict[str, Any]]
    selected_articles: List[Dict[str, Any]]
    project_title: Optional[str] = None
    project_structure: Optional[Dict[str, str]] = None


router = APIRouter()


@router.post("/create-project", response_model=Project)
def create_project(
    *, session: SessionDep, current_user: CurrentUser, data: ProjectCreateFromOnboarding
) -> Any:
    """
    Create a project from onboarding data.
    """
    # 0. Prepare LaTeX Content
    # Using a simple academic template
    abstract = (
        data.project_structure.get("abstract", "") if data.project_structure else ""
    )
    title = data.project_title or data.topic

    references_section = ""
    for a in data.selected_articles:
        references_section += (
            f"\\item {a.get('title')} ({a.get('year')}). {a.get('url')}\n"
        )

    latex_content = f"""\\documentclass{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage{{geometry}}
\\geometry{{a4paper, margin=1in}}
\\usepackage{{hyperref}}

\\title{{{title}}}
\\author{{{current_user.email}}}
\\date{{\\today}}

\\begin{{document}}

\\maketitle

\\begin{{abstract}}
{abstract}
\\end{{abstract}}

\\section{{Introduction}}
Placeholder for introduction.

\\section{{Methodology}}
Placeholder for methodology.

\\section{{References}}
\\begin{{itemize}}
{references_section}
\\end{{itemize}}

\\end{{document}}
"""

    # 1. Create Project
    project = Project(
        title=title,
        description=f"Generated via SciAgent Onboarding. Focus: {data.topic}",
        owner_id=current_user.id,
        content=latex_content,
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    # 2. Add Owner as Member
    member = ProjectMember(
        project_id=project.id,
        user_id=current_user.id,
        role=ProjectRole.OWNER,
        user_email=current_user.email,
    )
    session.add(member)

    # 3. Create Tasks
    for task_data in data.roadmap:
        task = ProjectTask(
            project_id=project.id,
            title=task_data.get("title"),
            description=task_data.get("description"),
            status=TaskStatus.PENDING,
            # deadline logic omitted for brevity, using simple addition if needed
        )
        session.add(task)

    session.commit()
    session.refresh(project)
    return project


class ChatRequest(BaseModel):
    message: str
    conversation_id: str
    project_context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    message: str
    structured_data: Optional[Dict[str, Any]] = (
        None  # e.g., suggested_articles, roadmap
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_onboarding(request: ChatRequest):
    """
    Chat with the Onboarding Agent.
    """
    # Initialize state with user message
    initial_state = {
        "messages": [HumanMessage(content=request.message)],
    }

    if request.project_context:
        if request.project_context.get("topic"):
            initial_state["topic"] = request.project_context["topic"]
        if request.project_context.get("selected_articles"):
            initial_state["selected_articles"] = request.project_context[
                "selected_articles"
            ]

    # Run Graph
    # Use conversation_id as thread_id for memory
    config = {"configurable": {"thread_id": request.conversation_id}}

    try:
        # Use invoke for synchronous execution (simpler for now)
        # For streaming, we'd use astream_events
        result = await onboarding_graph.ainvoke(initial_state, config=config)

        last_message = result["messages"][-1]
        response_content = (
            last_message.content
            if hasattr(last_message, "content")
            else str(last_message)
        )

        structured_data = {}
        if result.get("suggested_articles"):
            structured_data["suggested_articles"] = result["suggested_articles"]
        if result.get("roadmap"):
            structured_data["roadmap"] = result.get("roadmap")
        if result.get("project_title"):
            structured_data["project_title"] = result.get("project_title")
        if result.get("project_structure"):
            structured_data["project_structure"] = result.get("project_structure")

        return ChatResponse(
            message=response_content,
            structured_data=structured_data if structured_data else None,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
