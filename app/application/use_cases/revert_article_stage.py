from uuid import UUID
from typing import TYPE_CHECKING
from app.domain.repositories.article_repository import ArticleRepository
from app.domain.events.event_bus import EventBus
from app.domain.workflow.types import MacroStage
from app.application.dto.workflow import RevertStageRequest
from app.application.use_cases.advance_article_stage import ArticleNotFoundException


class RevertArticleStageUseCase:
    """
    Handles the business use case for reverting an Article's stage.
    """

    def __init__(self, article_repository: ArticleRepository, event_bus: EventBus):
        self.article_repository = article_repository
        self.event_bus = event_bus

    def execute(self, article_id: UUID, request: RevertStageRequest) -> None:
        article = self.article_repository.get_by_id(article_id)
        if not article:
            raise ArticleNotFoundException(f"Article with id {article_id} not found.")

        # Convert string to Enum
        try:
            target_stage = MacroStage(request.target_stage)
        except ValueError:
            raise ValueError(f"Invalid target stage: {request.target_stage}")

        # Execute Domain Logic
        article.revert_stage(
            target_stage=target_stage,
            user_role=request.user_role,
            user_id=request.user_id,
            reason=request.reason,
        )

        # Persist
        self.article_repository.save(article)

        # Dispatch
        events = article.get_domain_events()
        for event in events:
            self.event_bus.publish(event)

        article.clear_events()
