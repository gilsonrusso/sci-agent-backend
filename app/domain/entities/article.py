from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.domain.workflow.types import MacroStage, SectionStatus, Role
from app.domain.workflow.state_machine import (
    WorkflowEngine,
    ArticleStageAdvancedEvent,
    ArticleReturnedEvent,
)


class Section:
    id: UUID
    article_id: UUID
    status: SectionStatus
    assigned_to: Optional[UUID]

    def __init__(
        self,
        id: UUID,
        article_id: UUID,
        status: SectionStatus = SectionStatus.DRAFT,
        assigned_to: Optional[UUID] = None,
    ):
        self.id = id
        self.article_id = article_id
        self.status = status
        self.assigned_to = assigned_to


class Article:
    id: UUID
    title: str
    stage: MacroStage
    deadline: Optional[datetime]
    # In a real DDD setup, events are kept in a queue inside the aggregate
    _domain_events: list

    def __init__(
        self,
        id: UUID,
        title: str,
        stage: MacroStage = MacroStage.IDEATION,
        deadline: Optional[datetime] = None,
    ):
        self.id = id
        self.title = title
        self.stage = stage
        self.deadline = deadline
        self._domain_events = []

    def get_domain_events(self):
        return self._domain_events

    def clear_events(self):
        self._domain_events.clear()

    def advance_stage(self, user_role: Role, user_id: UUID):
        """Advances the article to the next stage using the workflow engine"""
        next_stage_map = WorkflowEngine._FORWARD_TRANSITIONS
        next_stage = next_stage_map.get(self.stage)

        if not next_stage:
            raise ValueError("Article is at final stage and cannot advance further.")

        WorkflowEngine.validate_transition(self.stage, next_stage, user_role)

        from_stage = self.stage
        self.stage = next_stage

        event = ArticleStageAdvancedEvent(
            article_id=self.id,
            from_stage=from_stage,
            to_stage=self.stage,
            user_id=user_id,
        )
        self._domain_events.append(event)

    def revert_stage(
        self,
        target_stage: MacroStage,
        user_role: Role,
        user_id: UUID,
        reason: Optional[str] = None,
    ):
        """Returns the article to a previous stage"""
        WorkflowEngine.validate_reversion(self.stage, target_stage, user_role)

        from_stage = self.stage
        self.stage = target_stage

        event = ArticleReturnedEvent(
            article_id=self.id,
            from_stage=from_stage,
            to_stage=self.stage,
            user_id=user_id,
            reason=reason,
        )
        self._domain_events.append(event)
