import uuid
from typing import Any
from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.deps import SessionDep, CurrentUser
from app.models.project import Project, ProjectCreate, ProjectPublic, ProjectUpdate
from app.models.project import Project, ProjectCreate, ProjectPublic, ProjectUpdate
from app.models.project_member import (
    ProjectMember,
    ProjectRole,
    ProjectMemberCreate,
    ProjectMemberPublic,
)
from app.models.user import User

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

    # Add owner as a member
    member = ProjectMember(
        project_id=project.id, user_id=current_user.id, role=ProjectRole.OWNER
    )
    session.add(member)
    session.commit()

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
        .join(ProjectMember, Project.id == ProjectMember.project_id)
        .where(ProjectMember.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    if current_user.is_superuser:
        statement = select(Project).offset(skip).limit(limit)

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

    if not current_user.is_superuser:
        member = session.get(ProjectMember, (id, current_user.id))
        if not member:
            raise HTTPException(status_code=403, detail="Not a member of this project")

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
        if not current_user.is_superuser:
            member = session.get(ProjectMember, (id, current_user.id))
            if not member or member.role not in [ProjectRole.OWNER, ProjectRole.EDITOR]:
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


@router.post("/{id}/members", response_model=ProjectMemberPublic)
def add_member(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    member_in: ProjectMemberCreate,
) -> Any:
    """
    Add a member to a project.
    """
    project = session.get(Project, id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Only OWNER can add members
    if not current_user.is_superuser:
        member = session.get(ProjectMember, (id, current_user.id))
        if not member or member.role != ProjectRole.OWNER:
            raise HTTPException(
                status_code=403, detail="Not enough permissions (Requires OWNER)"
            )

    # Find user by email
    statement = select(User).where(User.email == member_in.email)
    user_to_add = session.exec(statement).first()
    if not user_to_add:
        raise HTTPException(status_code=404, detail="User with this email not found")

    # Check if already a member
    existing_member = session.get(ProjectMember, (id, user_to_add.id))
    if existing_member:
        raise HTTPException(status_code=400, detail="User is already a member")

    # Add member
    new_member = ProjectMember(
        project_id=id, user_id=user_to_add.id, role=member_in.role
    )
    session.add(new_member)
    session.commit()
    session.refresh(new_member)

    return ProjectMemberPublic(
        project_id=new_member.project_id,
        user_id=new_member.user_id,
        role=new_member.role,
        user_email=user_to_add.email,
        user_full_name=user_to_add.full_name,
    )


@router.delete("/{id}/members/{user_id}", response_model=Any)
def remove_member(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    user_id: uuid.UUID,
) -> Any:
    """
    Remove a member from a project.
    """
    project = session.get(Project, id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Only OWNER can remove members (except removing themselves?)
    if not current_user.is_superuser:
        member = session.get(ProjectMember, (id, current_user.id))
        if not member or member.role != ProjectRole.OWNER:
            # Allow user to leave? Maybe later.
            raise HTTPException(
                status_code=403, detail="Not enough permissions (Requires OWNER)"
            )

    member_to_remove = session.get(ProjectMember, (id, user_id))
    if not member_to_remove:
        raise HTTPException(status_code=404, detail="Member not found")

    if (
        member_to_remove.role == ProjectRole.OWNER
        and member_to_remove.user_id == current_user.id
    ):
        raise HTTPException(status_code=400, detail="Owner cannot remove themselves")

    session.delete(member_to_remove)
    session.commit()
    return {"status": "success"}


@router.get("/{id}/members", response_model=list[ProjectMemberPublic])
def read_members(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
) -> Any:
    """
    List members of a project.
    """
    project = session.get(Project, id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if current user has access to view members (Member of project)
    if not current_user.is_superuser:
        member = session.get(ProjectMember, (id, current_user.id))
        if not member:
            raise HTTPException(status_code=403, detail="Not a member of this project")

    statement = select(ProjectMember).where(ProjectMember.project_id == id)
    members = session.exec(statement).all()

    # Enrich with user info
    result = []
    for m in members:
        user = session.get(User, m.user_id)
        if user:
            result.append(
                ProjectMemberPublic(
                    project_id=m.project_id,
                    user_id=m.user_id,
                    role=m.role,
                    user_email=user.email,
                    user_full_name=user.full_name,
                )
            )

    return result
