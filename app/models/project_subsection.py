import uuid
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship, Column, String
from app.core.workflow import SectionStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .project import Project


class ProjectSubsection(SQLModel, table=True):
    __tablename__ = "project_subsections"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id")

    title: str = Field(index=True)
    status: SectionStatus = Field(default=SectionStatus.DRAFT, sa_column=Column(String))
    assigned_to_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")

    project: "Project" = Relationship(back_populates="subsections")
