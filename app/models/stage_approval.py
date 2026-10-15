import uuid
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship, Column, String
from app.core.workflow import MacroStage
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .project import Project


class StageApproval(SQLModel, table=True):
    __tablename__ = "stage_approvals"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id")

    from_stage: MacroStage = Field(sa_column=Column(String))
    to_stage: MacroStage = Field(sa_column=Column(String))

    approved_by_id: uuid.UUID = Field(foreign_key="users.id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Optional comment/justification provided during signing
    comment: str | None = None

    project: "Project" = Relationship(back_populates="approvals")
