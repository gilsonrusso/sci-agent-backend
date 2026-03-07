from typing import Optional, List
from uuid import UUID
from sqlmodel import Session, select
from app.domain.repositories.task_repository import TaskRepository
from app.domain.entities.task import DomainTask, TaskStatus
from app.models.project_task import ProjectTask


class SQLTaskRepository(TaskRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, task_id: UUID) -> Optional[DomainTask]:
        db_task = self.session.get(ProjectTask, task_id)
        if not db_task:
            return None

        return DomainTask(
            id=db_task.id,
            project_id=db_task.project_id,
            title=db_task.title,
            description=db_task.description,
            status=TaskStatus(db_task.status),
            assigned_to=db_task.assigned_to,
            due_date=db_task.due_date,
        )

    def save(self, task: DomainTask) -> None:
        db_task = self.session.get(ProjectTask, task.id)
        if not db_task:
            # Create new
            db_task = ProjectTask(
                id=task.id,
                project_id=task.project_id,
                title=task.title,
                description=task.description,
                status=task.status.value,
                assigned_to=task.assigned_to,
                due_date=task.due_date,
            )
            self.session.add(db_task)
        else:
            # Update existing
            db_task.title = task.title
            db_task.description = task.description
            db_task.status = task.status.value
            db_task.assigned_to = task.assigned_to
            db_task.due_date = task.due_date

        self.session.commit()
        self.session.refresh(db_task)

    def get_by_project(self, project_id: UUID) -> List[DomainTask]:
        statement = select(ProjectTask).where(ProjectTask.project_id == project_id)
        db_tasks = self.session.exec(statement).all()

        return [
            DomainTask(
                id=t.id,
                project_id=t.project_id,
                title=t.title,
                description=t.description,
                status=TaskStatus(t.status),
                assigned_to=t.assigned_to,
                due_date=t.due_date,
            )
            for t in db_tasks
        ]
