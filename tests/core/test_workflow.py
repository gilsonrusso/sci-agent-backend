import pytest
from app.core.workflow import MacroStage, Role, WorkflowEngine, TransitionError


def test_workflow_engine_can_transition():
    # Valid forward transitions
    assert (
        WorkflowEngine.can_transition(
            MacroStage.IDEATION, MacroStage.RESEARCH, Role.AUTHOR
        )
        is True
    )
    # Invalid role
    assert (
        WorkflowEngine.can_transition(
            MacroStage.HUMAN_REVIEW, MacroStage.APPROVED, Role.AUTHOR
        )
        is False
    )
    # Invalid step
    assert (
        WorkflowEngine.can_transition(
            MacroStage.IDEATION, MacroStage.WRITING, Role.AUTHOR
        )
        is False
    )


def test_workflow_engine_validate_transition_success():
    # Author can move from ideation to research
    WorkflowEngine.validate_transition(
        MacroStage.IDEATION, MacroStage.RESEARCH, Role.AUTHOR
    )
    # Mentor can approve
    WorkflowEngine.validate_transition(
        MacroStage.HUMAN_REVIEW, MacroStage.APPROVED, Role.MENTOR
    )


def test_workflow_engine_validate_transition_invalid_next():
    with pytest.raises(TransitionError) as exc:
        WorkflowEngine.validate_transition(
            MacroStage.IDEATION, MacroStage.WRITING, Role.AUTHOR
        )
    assert "Invalid transition from MacroStage.IDEATION to MacroStage.WRITING" in str(
        exc.value
    )


def test_workflow_engine_validate_transition_invalid_role():
    with pytest.raises(TransitionError) as exc:
        WorkflowEngine.validate_transition(
            MacroStage.HUMAN_REVIEW, MacroStage.APPROVED, Role.AUTHOR
        )
    assert (
        "is not authorized to transition to MacroStage.APPROVED" in str(exc.value)
    )


def test_workflow_engine_validate_reversion_success():
    # Author can revert from research to ideation
    WorkflowEngine.validate_reversion(
        MacroStage.RESEARCH, MacroStage.IDEATION, Role.AUTHOR
    )
    # Mentor can revert from human review to writing
    WorkflowEngine.validate_reversion(
        MacroStage.HUMAN_REVIEW, MacroStage.WRITING, Role.MENTOR
    )


def test_workflow_engine_validate_reversion_same_stage():
    with pytest.raises(TransitionError) as exc:
        WorkflowEngine.validate_reversion(
            MacroStage.RESEARCH, MacroStage.RESEARCH, Role.AUTHOR
        )
    assert "Cannot return to the same stage" in str(exc.value)


def test_workflow_engine_validate_reversion_forward_attempt():
    with pytest.raises(TransitionError) as exc:
        WorkflowEngine.validate_reversion(
            MacroStage.IDEATION, MacroStage.RESEARCH, Role.AUTHOR
        )
    assert "Reversion must go backwards" in str(exc.value)


def test_workflow_engine_validate_reversion_author_from_finalized():
    with pytest.raises(TransitionError) as exc:
        WorkflowEngine.validate_reversion(
            MacroStage.APPROVED, MacroStage.HUMAN_REVIEW, Role.AUTHOR
        )
    assert "cannot revert from finalized stages" in str(exc.value)
