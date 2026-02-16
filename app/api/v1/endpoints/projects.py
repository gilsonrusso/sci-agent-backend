import uuid
from typing import Any
from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.deps import SessionDep, CurrentUser
from app.models.project import Project, ProjectCreate, ProjectPublic, ProjectUpdate

router = APIRouter()


from app.models.template import Template

DEFAULT_LATEX_TEMPLATE = ""  # Removed, keeping variable to avoid reference errors if any, but logic below uses DB. Actually better to remove it.


@router.post("/", response_model=ProjectPublic)
def create_project(
    *, session: SessionDep, current_user: CurrentUser, project_in: ProjectCreate
) -> Any:
    """
    Create new project.
    """
    if not project_in.content:
        # Fetch default template from DB
        statement = select(Template).where(Template.is_default == True)
        default_template = session.exec(statement).first()

        if default_template:
            project_in.content = default_template.content
        else:
            # Fallback (should not happen if init_db ran)
            project_in.content = r"\documentclass{article}\begin{document}No default template found.\end{document}"

    project = Project.model_validate(project_in, update={"owner_id": current_user.id})
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.get("/", response_model=list[ProjectPublic])
def read_projects(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve projects.
    """
    statement = (
        select(Project)
        .where(Project.owner_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    projects = session.exec(statement).all()
    return projects


@router.get("/{id}", response_model=ProjectPublic)
def read_project(
    *, session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """
    Get project by ID.
    """
    project = session.get(Project, id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return project


@router.put("/{id}", response_model=ProjectPublic)
def update_project(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    project_in: ProjectUpdate,
) -> Any:
    """
    Update a project.
    """
    project = session.get(Project, id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    update_data = project_in.model_dump(exclude_unset=True)
    project.sqlmodel_update(update_data)
    project.updated_at = datetime.utcnow()

    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.delete("/{id}", response_model=ProjectPublic)
def delete_project(
    *, session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """
    Delete a project.
    """
    project = session.get(Project, id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    session.delete(project)
    session.commit()
    return project
