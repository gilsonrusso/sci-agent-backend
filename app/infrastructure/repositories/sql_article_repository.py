from typing import Optional, List
from uuid import UUID
from sqlmodel import Session, select
from datetime import datetime

from app.domain.entities.article import Article
from app.domain.repositories.article_repository import ArticleRepository
from app.domain.workflow.types import MacroStage
from app.models.project import Project


class SQLArticleRepository(ArticleRepository):
    """
    Implementation of the ArticleRepository using SQLAlchemy/SQLModel.
    Provides mapping between the pure Domain Entity and the DB Model.
    """

    def __init__(self, session: Session):
        self.session = session

    def _to_domain(self, project: Project) -> Article:
        return Article(
            id=project.id,
            title=project.title,
            stage=project.stage,
            deadline=project.deadline,
        )

    def _update_model(self, model: Project, entity: Article):
        # We only map the fields that Domain Entity can change
        model.stage = entity.stage

    def get_by_id(self, article_id: UUID) -> Optional[Article]:
        project = self.session.get(Project, article_id)
        if not project:
            return None
        return self._to_domain(project)

    def save(self, article: Article) -> None:
        project = self.session.get(Project, article.id)
        if project:
            self._update_model(project, article)
            self.session.add(project)
            self.session.commit()
            self.session.refresh(project)
        else:
            # creating a new article from scratch is handled elsewhere (Project creation API)
            pass

    def get_all(self) -> List[Article]:
        statement = select(Project)
        projects = self.session.exec(statement).all()
        return [self._to_domain(p) for p in projects]
