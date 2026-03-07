from enum import Enum
from uuid import UUID
from datetime import datetime


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
