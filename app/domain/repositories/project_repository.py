from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID
from app.models.project import Project
from app.models.project_task import ProjectTask


class ProjectRepository(ABC):
    @abstractmethod
    def create(self, project: Project, tasks: List[ProjectTask]) -> Project:
        pass

    @abstractmethod
    def get_by_id(self, project_id: UUID) -> Optional[Project]:
        pass
