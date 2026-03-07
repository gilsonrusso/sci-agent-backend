from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID

from app.api.deps import SessionDep, CurrentUser
from app.infrastructure.repositories.sql_task_repository import SQLTaskRepository
from app.application.use_cases.tasks.update_task_use_case import UpdateTaskUseCase
from app.domain.entities.task import TaskStatus
from app.domain.workflow.types import Role

router = APIRouter()


class TaskUpdateSchema(BaseModel):
    status: Optional[TaskStatus] = None
    assigned_to: Optional[UUID] = None


class TaskResponseSchema(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: Optional[str] = None
    status: TaskStatus
    assigned_to: Optional[UUID] = None


@router.patch("/{task_id}", response_model=TaskResponseSchema)
def update_task(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    task_id: UUID,
    data: TaskUpdateSchema,
):
    """
    Update task status or assignment using DDD Use Case.
    """
    repo = SQLTaskRepository(session)
    use_case = UpdateTaskUseCase(repo)

    # In a real system, we'd fetch the user's role in the specific project.
    # For now, we'll use a placeholder role or fetch from context.
    user_role = Role.AUTHOR  # Placeholder

    try:
        updated_task = use_case.execute(
            task_id=task_id,
            user_id=current_user.id,
            user_role=user_role,
            new_status=data.status,
            new_assignee=data.assigned_to,
        )
        return updated_task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_id}", response_model=List[TaskResponseSchema])
def list_project_tasks(
    *, session: SessionDep, current_user: CurrentUser, project_id: UUID
):
    """List all tasks for a project."""
    repo = SQLTaskRepository(session)
    return repo.get_by_project(project_id)
