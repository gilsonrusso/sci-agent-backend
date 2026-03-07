from uuid import UUID
from typing import Optional
from app.domain.repositories.task_repository import TaskRepository
from app.domain.entities.task import TaskStatus
from app.domain.workflow.types import Role


class UpdateTaskUseCase:
    def __init__(self, task_repo: TaskRepository):
        self.task_repo = task_repo

    def execute(
        self,
        task_id: UUID,
        user_id: UUID,
        user_role: Role,
        new_status: Optional[TaskStatus] = None,
        new_assignee: Optional[UUID] = None,
    ):
        # 1. Retrieve Task
        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found.")

        # 2. Permission Check (Business Rule)
        # Authors can move tasks between PENDING and IN_PROGRESS.
        # WAITING_APPROVAL and DONE might need COORDINATOR/MENTOR for final seal,
        # but for now let's allow basic movement if they are part of the project.
        # (Detailed RBAC can be expanded here)

        # 3. Apply Changes
        if new_status:
            task.transition_to(new_status)

        if new_assignee:
            # US04: Assignment
            task.assign_to(new_assignee)

        # 4. Save
        self.task_repo.save(task)

        return task
