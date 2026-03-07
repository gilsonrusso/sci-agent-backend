from uuid import UUID
from typing import TYPE_CHECKING
from app.domain.repositories.article_repository import ArticleRepository
from app.domain.events.event_bus import EventBus
from app.application.dto.workflow import AdvanceStageRequest


class ArticleNotFoundException(Exception):
    pass


class AdvanceArticleStageUseCase:
    """
    Handles the business use case for advancing an Article's stage.
    It coordinates the entity, the repository, and the event bus.
    """

    def __init__(self, article_repository: ArticleRepository, event_bus: EventBus):
        self.article_repository = article_repository
        self.event_bus = event_bus

    def execute(self, article_id: UUID, request: AdvanceStageRequest) -> None:
        # 1. Load the Entity
        article = self.article_repository.get_by_id(article_id)
        if not article:
            raise ArticleNotFoundException(f"Article with id {article_id} not found.")

        # 2. Execute Domain Logic
        # (This will internally validate against WorkflowEngine and create domain events)
        article.advance_stage(user_role=request.user_role, user_id=request.user_id)

        # 3. Persist State Changes
        self.article_repository.save(article)

        # 4. Dispatch Domain Events
        events = article.get_domain_events()
        for event in events:
            self.event_bus.publish(event)

        # Clear events after dispatch to avoid republishing
        article.clear_events()
