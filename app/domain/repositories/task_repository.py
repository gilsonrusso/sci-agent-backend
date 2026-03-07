from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from app.domain.entities.task import DomainTask


class TaskRepository(ABC):
    @abstractmethod
    def get_by_id(self, task_id: UUID) -> Optional[DomainTask]:
        """Retrieve a task by its ID."""
        pass

    @abstractmethod
    def save(self, task: DomainTask) -> None:
        """Save or update a task."""
        pass

    @abstractmethod
    def get_by_project(self, project_id: UUID) -> List[DomainTask]:
        """Retrieve all tasks for a specific project."""
        pass
