import pytest
import uuid
from datetime import datetime

from app.domain.entities.article import Article
from app.domain.workflow.types import MacroStage, Role
from app.domain.workflow.state_machine import (
    TransitionError,
    ArticleStageAdvancedEvent,
    ArticleReturnedEvent,
)


def test_article_starts_at_ideation():
    article = Article(id=uuid.uuid4(), title="Test Article")
    assert article.stage == MacroStage.IDEATION


def test_author_can_advance_ideation_to_research():
    article = Article(id=uuid.uuid4(), title="Test Article")
    user_id = uuid.uuid4()

    article.advance_stage(user_role=Role.AUTHOR, user_id=user_id)

    assert article.stage == MacroStage.RESEARCH
    events = article.get_domain_events()
    assert len(events) == 1
    assert isinstance(events[0], ArticleStageAdvancedEvent)
    assert events[0].to_stage == MacroStage.RESEARCH
    assert events[0].user_id == user_id


def test_author_cannot_approve_article():
    article = Article(
        id=uuid.uuid4(), title="Test Article", stage=MacroStage.HUMAN_REVIEW
    )
    user_id = uuid.uuid4()

    with pytest.raises(TransitionError) as exc_info:
        article.advance_stage(user_role=Role.AUTHOR, user_id=user_id)

    assert "not authorized to transition to MacroStage.APPROVED" in str(exc_info.value)
    assert article.stage == MacroStage.HUMAN_REVIEW
    assert len(article.get_domain_events()) == 0


def test_mentor_can_approve_article():
    article = Article(
        id=uuid.uuid4(), title="Test Article", stage=MacroStage.HUMAN_REVIEW
    )
    user_id = uuid.uuid4()

    article.advance_stage(user_role=Role.MENTOR, user_id=user_id)

    assert article.stage == MacroStage.APPROVED


def test_coordinator_can_submit_article():
    article = Article(id=uuid.uuid4(), title="Test Article", stage=MacroStage.APPROVED)
    user_id = uuid.uuid4()

    article.advance_stage(user_role=Role.COORDINATOR, user_id=user_id)

    assert article.stage == MacroStage.SUBMITTED


def test_invalid_forward_transition_skipping_stages():
    article = Article(id=uuid.uuid4(), title="Test Article", stage=MacroStage.IDEATION)
    user_id = uuid.uuid4()

    with pytest.raises(TransitionError) as exc_info:
        # Can't jump straight to WRITING, must go to RESEARCH first, but WorkflowEngine validates current->expected next
        # To simulate a jump, we'd have to hack the engine, but the engine strictly uses _FORWARD_TRANSITIONS
        # The advance_stage method forces the next stage automatically based on current
        article.advance_stage(user_role=Role.AUTHOR, user_id=user_id)
        article.advance_stage(user_role=Role.AUTHOR, user_id=user_id)
        # We manually try to set an invalid next stage via WorkflowEngine directly to test the check
        from app.domain.workflow.state_machine import WorkflowEngine

        WorkflowEngine.validate_transition(
            MacroStage.IDEATION, MacroStage.WRITING, Role.AUTHOR
        )

    assert "Invalid transition from MacroStage.IDEATION to MacroStage.WRITING" in str(
        exc_info.value
    )


def test_author_cannot_revert_from_approved():
    article = Article(id=uuid.uuid4(), title="Test Article", stage=MacroStage.APPROVED)
    user_id = uuid.uuid4()

    with pytest.raises(TransitionError) as exc_info:
        article.revert_stage(
            target_stage=MacroStage.HUMAN_REVIEW, user_role=Role.AUTHOR, user_id=user_id
        )

    assert "cannot revert from finalized stages" in str(exc_info.value)


def test_mentor_can_revert_from_human_review_to_writing():
    article = Article(
        id=uuid.uuid4(), title="Test Article", stage=MacroStage.HUMAN_REVIEW
    )
    user_id = uuid.uuid4()

    article.revert_stage(
        target_stage=MacroStage.WRITING,
        user_role=Role.MENTOR,
        user_id=user_id,
        reason="Needs more citations",
    )

    assert article.stage == MacroStage.WRITING
    events = article.get_domain_events()
    assert len(events) == 1
    assert isinstance(events[0], ArticleReturnedEvent)
    assert events[0].to_stage == MacroStage.WRITING
    assert events[0].reason == "Needs more citations"


def test_revert_must_go_backwards():
    article = Article(id=uuid.uuid4(), title="Test Article", stage=MacroStage.RESEARCH)
    user_id = uuid.uuid4()

    with pytest.raises(TransitionError) as exc_info:
        article.revert_stage(
            target_stage=MacroStage.WRITING, user_role=Role.MENTOR, user_id=user_id
        )

    assert "Reversion must go backwards" in str(exc_info.value)
