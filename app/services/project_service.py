from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlmodel import Session

from app.models.project import Project
from app.models.project_task import ProjectTask, TaskStatus
from app.models.project_member import ProjectMember, ProjectRole


def create_project_from_onboarding(
    session: Session,
    user_id: UUID,
    title: str,
    abstract: str,
    tasks: List[Dict[str, Any]],
    articles: List[Dict[str, Any]],
    topic: str,
) -> Project:
    """
    Creates a new project with its initial roadmap (tasks) and owner membership
    based on onboarding data in a simple, flat service.
    """
    # 1. Validation
    if not topic:
        raise ValueError("O tópico da pesquisa é obrigatório.")
    if not title:
        raise ValueError("O título do projeto é obrigatório.")
    if not tasks:
        raise ValueError("O roadmap inicial deve conter pelo menos uma tarefa.")

    # 2. Build LaTeX content template
    references_section = ""
    for a in articles:
        references_section += (
            f"\\item {a.get('title')} ({a.get('year')}). {a.get('url')}\n"
        )

    latex_content = f"""\\documentclass[conference]{{IEEEtran}}
\\IEEEoverridecommandlockouts
\\usepackage{{cite}}
\\usepackage{{amsmath,amssymb,amsfonts}}
\\usepackage{{algorithmic}}
\\usepackage{{graphicx}}
\\usepackage{{textcomp}}
\\usepackage{{xcolor}}

\\begin{{document}}
\\title{{{title}}}

\\maketitle

\\begin{{abstract}}
{abstract}
\\end{{abstract}}

\\section{{Introduction}}
Esta seção foi gerada automaticamente para o tema: {topic}.

\\section{{References}}
\\begin{{itemize}}
{references_section}
\\end{{itemize}}

\\end{{document}}
"""

    # 3. Create Project Model
    project = Project(
        title=title,
        description=f"Generated via SciAgent Onboarding. Focus: {topic}",
        owner_id=user_id,
        content=latex_content,
    )
    session.add(project)
    session.flush()  # Ensures the ID is generated and available

    # 4. Map and add initial roadmap tasks
    for i, t in enumerate(tasks):
        due_in_days = t.get("due_in_days", 7)
        task = ProjectTask(
            project_id=project.id,
            title=t.get("title", f"Tarefa {i+1}"),
            description=t.get("description", ""),
            status=TaskStatus.PENDING,
            due_date=datetime.utcnow() + timedelta(days=due_in_days),
        )
        session.add(task)

    # 5. Add owner as a member
    owner_member = ProjectMember(
        project_id=project.id,
        user_id=user_id,
        role=ProjectRole.OWNER,
    )
    session.add(owner_member)

    # 6. Commit transaction and refresh project
    session.commit()
    session.refresh(project)

    return project
