from uuid import UUID
from datetime import datetime
from typing import Optional, List
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_APPROVAL = "waiting_approval"
    DONE = "done"


class DomainTask:
    def __init__(
        self,
        id: UUID,
        project_id: UUID,
        title: str,
        description: Optional[str] = None,
        status: TaskStatus = TaskStatus.PENDING,
        assigned_to: Optional[UUID] = None,
        due_date: Optional[datetime] = None,
    ):
        self.id = id
        self.project_id = project_id
        self.title = title
        self.description = description
        self.status = status
        self.assigned_to = assigned_to
        self.due_date = due_date

    def transition_to(self, new_status: TaskStatus):
        """
        Validate and perform status transition.
        Business Rules:
        - Cannot move back to PENDING from DONE.
        - Moving to DONE might require specific roles (to be handled in Use Case).
        """
        if self.status == TaskStatus.DONE and new_status == TaskStatus.PENDING:
            raise ValueError(
                "Não é possível mover uma tarefa concluída de volta para Pendente."
            )

        self.status = new_status

    def assign_to(self, user_id: UUID):
        """Assigns the task to a user."""
        self.assigned_to = user_id
