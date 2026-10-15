from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlmodel import Session

from app.models.project_task import ProjectTask, TaskStatus
from app.core.workflow import Role


def update_task(
    session: Session,
    task_id: UUID,
    user_id: UUID,
    user_role: Role,
    new_status: Optional[TaskStatus] = None,
    new_assignee: Optional[UUID] = None,
) -> ProjectTask:
    """
    Updates task status or assignment with business rule validations in a simple service.
    """
    # 1. Retrieve Task
    task = session.get(ProjectTask, task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found.")

    # 2. Validate and apply status transition
    if new_status:
        # Convert string to TaskStatus enum if needed
        if isinstance(new_status, str):
            try:
                new_status = TaskStatus(new_status)
            except ValueError:
                raise ValueError(f"Status inválido: {new_status}")

        # Business Rule: Cannot move back to PENDING from DONE
        if task.status == TaskStatus.DONE and new_status == TaskStatus.PENDING:
            raise ValueError(
                "Não é possível mover uma tarefa concluída de volta para Pendente."
            )
        task.status = new_status

    # 3. Update assignee
    if new_assignee:
        task.assigned_to = new_assignee

    task.updated_at = datetime.utcnow()

    # 4. Persist
    session.add(task)
    session.commit()
    session.refresh(task)

    return task
