import uuid
from typing import Any, List

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.deps import SessionDep, CurrentUser
from app.models.project import Project
from app.models.project_member import ProjectMember, ProjectRole
from app.models.project_task import (
    ProjectTask,
    ProjectTaskCreate,
    ProjectTaskUpdate,
    TaskStatus,
)
from app.services.audit_service import log_action

router = APIRouter()


@router.post("/", response_model=ProjectTask)
def create_task(
    *, session: SessionDep, current_user: CurrentUser, task_in: ProjectTaskCreate
) -> Any:
    """
    Create a new task.
    """
    project = session.get(Project, task_in.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check permissions (Member can create tasks?)
    # Assuming any member can create tasks for now.
    member = session.get(ProjectMember, (task_in.project_id, current_user.id))
    if not current_user.is_superuser and not member:
        raise HTTPException(status_code=403, detail="Not a member of this project")

    task = ProjectTask.model_validate(task_in)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.get("/", response_model=List[ProjectTask])
def read_tasks(
    session: SessionDep,
    current_user: CurrentUser,
    project_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve tasks for a project.
    """
    # Check permissions
    if not current_user.is_superuser:
        member = session.get(ProjectMember, (project_id, current_user.id))
        if not member:
            raise HTTPException(status_code=403, detail="Not a member of this project")

    statement = (
        select(ProjectTask)
        .where(ProjectTask.project_id == project_id)
        .offset(skip)
        .limit(limit)
    )
    tasks = session.exec(statement).all()
    return tasks


@router.put("/{id}", response_model=ProjectTask)
def update_task(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    task_in: ProjectTaskUpdate,
) -> Any:
    """
    Update a task.
    """
    task = session.get(ProjectTask, id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check permissions
    if not current_user.is_superuser:
        member = session.get(ProjectMember, (task.project_id, current_user.id))
        if not member:
            raise HTTPException(status_code=403, detail="Not a member of this project")

    # Audit Status Changes
    if task_in.status and task_in.status != task.status:
        # LOGGING
        log_action(
            session,
            project_id=task.project_id,
            actor_id=current_user.id,
            action_type="TASK_STATUS_CHANGE",
            previous_value={"status": task.status},
            new_value={"status": task_in.status},
            justification=f"Task {task.title} updated",
        )

    update_data = task_in.model_dump(exclude_unset=True)
    task.sqlmodel_update(update_data)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.post("/{id}/request-approval", response_model=ProjectTask)
def request_approval(
    *, session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """
    Request approval for a task (Student -> Supervisor).
    """
    task = session.get(ProjectTask, id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Verify membership
    member = session.get(ProjectMember, (task.project_id, current_user.id))
    if not current_user.is_superuser and not member:
        raise HTTPException(status_code=403, detail="Not a member")

    # State transition
    previous_status = task.status
    task.status = TaskStatus.WAITING_APPROVAL
    session.add(task)

    # Log
    log_action(
        session,
        project_id=task.project_id,
        actor_id=current_user.id,
        action_type="TASK_APPROVAL_REQUEST",
        previous_value={"status": previous_status},
        new_value={"status": TaskStatus.WAITING_APPROVAL},
        justification="User requested approval",
    )
    session.commit()
    session.refresh(task)
    return task


@router.post("/{id}/approve", response_model=ProjectTask)
def approve_task(
    *, session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """
    Approve a task (Supervisor Only).
    """
    task = session.get(ProjectTask, id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check Supervisor Role
    if not current_user.is_superuser:
        member = session.get(ProjectMember, (task.project_id, current_user.id))
        if not member or member.role not in [
            ProjectRole.OWNER,
            ProjectRole.EDITOR,
        ]:  # Assuming Owner/Editor=Supervisor
            raise HTTPException(
                status_code=403, detail="Only Owners/Editors can approve tasks"
            )

    previous_status = task.status
    task.status = TaskStatus.DONE
    session.add(task)

    log_action(
        session,
        project_id=task.project_id,
        actor_id=current_user.id,
        action_type="TASK_APPROVED",
        previous_value={"status": previous_status},
        new_value={"status": TaskStatus.DONE},
        justification="Supervisor approved task",
    )
    session.commit()
    session.refresh(task)
    return task


@router.post("/{id}/reject", response_model=ProjectTask)
def reject_task(
    *, session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """
    Reject a task (Supervisor Only).
    """
    task = session.get(ProjectTask, id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check Supervisor Role
    if not current_user.is_superuser:
        member = session.get(ProjectMember, (task.project_id, current_user.id))
        if not member or member.role not in [ProjectRole.OWNER, ProjectRole.EDITOR]:
            raise HTTPException(
                status_code=403, detail="Only Owners/Editors can reject tasks"
            )

    previous_status = task.status
    task.status = TaskStatus.IN_PROGRESS  # Send back to in_progress
    session.add(task)

    log_action(
        session,
        project_id=task.project_id,
        actor_id=current_user.id,
        action_type="TASK_REJECTED",
        previous_value={"status": previous_status},
        new_value={"status": TaskStatus.IN_PROGRESS},
        justification="Supervisor rejected task",
    )
    session.commit()
    session.refresh(task)
    return task
