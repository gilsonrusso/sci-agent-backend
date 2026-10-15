from enum import Enum
from typing import Optional
from uuid import UUID


class MacroStage(str, Enum):
    IDEATION = "IDEATION"
    RESEARCH = "RESEARCH"
    WRITING = "WRITING"
    AI_REVIEW = "AI_REVIEW"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    APPROVED = "APPROVED"
    SUBMITTED = "SUBMITTED"


class SectionStatus(str, Enum):
    DRAFT = "DRAFT"
    WRITING = "WRITING"
    DONE = "DONE"


class Role(str, Enum):
    AUTHOR = "AUTHOR"
    MENTOR = "MENTOR"
    COORDINATOR = "COORDINATOR"


class TransitionError(ValueError):
    """Exception raised when an invalid state transition is attempted."""

    pass


class WorkflowEngine:
    """Finite State Machine for Article stages."""

    # Define strict forward transitions
    # from_stage -> next valid stage
    _FORWARD_TRANSITIONS = {
        MacroStage.IDEATION: MacroStage.RESEARCH,
        MacroStage.RESEARCH: MacroStage.WRITING,
        MacroStage.WRITING: MacroStage.AI_REVIEW,
        MacroStage.AI_REVIEW: MacroStage.HUMAN_REVIEW,
        MacroStage.HUMAN_REVIEW: MacroStage.APPROVED,
        MacroStage.APPROVED: MacroStage.SUBMITTED,
    }

    # Define gatekeepers for transitions (Target Stage -> Roles that can move TO that stage)
    _GATEKEEPERS = {
        MacroStage.RESEARCH: {Role.AUTHOR, Role.MENTOR, Role.COORDINATOR},
        MacroStage.WRITING: {Role.AUTHOR, Role.MENTOR, Role.COORDINATOR},
        MacroStage.AI_REVIEW: {Role.AUTHOR, Role.MENTOR, Role.COORDINATOR},
        MacroStage.HUMAN_REVIEW: {Role.AUTHOR, Role.MENTOR, Role.COORDINATOR},
        MacroStage.APPROVED: {Role.MENTOR},  # Only MENTOR can approve
        MacroStage.SUBMITTED: {
            Role.MENTOR,
            Role.COORDINATOR,
        },  # Submissions need authority
    }

    @classmethod
    def can_transition(
        cls, current_stage: MacroStage, next_stage: MacroStage, user_role: Role
    ) -> bool:
        """Check if a transition is valid without raising an error."""
        try:
            cls.validate_transition(current_stage, next_stage, user_role)
            return True
        except TransitionError:
            return False

    @classmethod
    def validate_transition(
        cls, current_stage: MacroStage, next_stage: MacroStage, user_role: Role
    ):
        """Validates if standard moving forward is allowed from current stage with given role"""

        # 1. Check if it's a valid forward transition
        expected_next = cls._FORWARD_TRANSITIONS.get(current_stage)
        if expected_next != next_stage:
            raise TransitionError(
                f"Invalid transition from {current_stage} to {next_stage}. Expected {expected_next}"
            )

        # 2. Check Role permissions
        allowed_roles = cls._GATEKEEPERS.get(next_stage, set())
        if user_role not in allowed_roles:
            raise TransitionError(
                f"Role {user_role} is not authorized to transition to {next_stage}. Allowed: {allowed_roles}"
            )

    @classmethod
    def validate_reversion(
        cls, current_stage: MacroStage, target_stage: MacroStage, user_role: Role
    ):
        """Validates returning to a previous state"""
        if current_stage == target_stage:
            raise TransitionError("Cannot return to the same stage")

        # Verify it's actually backwards (checking index of Enums)
        stages = list(MacroStage)
        current_idx = stages.index(current_stage)
        target_idx = stages.index(target_stage)

        if target_idx >= current_idx:
            raise TransitionError(
                f"Cannot revert from {current_stage} to {target_stage}. Reversion must go backwards."
            )

        # Optionally add gatekeepers for reversions (e.g. only MENTOR can revert from APPROVED)
        if (
            current_stage in [MacroStage.APPROVED, MacroStage.SUBMITTED]
            and user_role == Role.AUTHOR
        ):
            raise TransitionError(
                f"Role {user_role} cannot revert from finalized stages."
            )
