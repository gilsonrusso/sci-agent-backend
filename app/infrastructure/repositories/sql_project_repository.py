from typing import List, Optional
from uuid import UUID
from sqlmodel import Session
from app.domain.repositories.project_repository import ProjectRepository
from app.models.project import Project
from app.models.project_task import ProjectTask
from app.models.project_member import ProjectMember, ProjectRole


class SQLProjectRepository(ProjectRepository):
    def __init__(self, session: Session):
        self.session = session

    def create(self, project: Project, tasks: List[ProjectTask]) -> Project:
        self.session.add(project)
        self.session.flush()  # To get the ID

        # Add tasks
        for task in tasks:
            task.project_id = project.id
            self.session.add(task)

        # Add owner as member automatically if not already there
        # This is a business rule that could be in a domain service, but
        # for infrastructure convenience, we ensure consistency here.
        owner_member = ProjectMember(
            project_id=project.id, user_id=project.owner_id, role=ProjectRole.OWNER
        )
        self.session.add(owner_member)

        self.session.commit()
        self.session.refresh(project)
        return project

    def get_by_id(self, project_id: UUID) -> Optional[Project]:
        return self.session.get(Project, project_id)
