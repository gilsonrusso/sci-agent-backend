import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship, Column, String
from app.domain.workflow.types import MacroStage
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .project_member import ProjectMember
    from .project_subsection import ProjectSubsection
    from .stage_approval import StageApproval


class ProjectBase(SQLModel):
    title: str = Field(index=True)
    description: Optional[str] = None
    content: Optional[str] = None  # Stores LaTeX/Markdown content
    stage: MacroStage = Field(default=MacroStage.IDEATION, sa_column=Column(String))
    deadline: Optional[datetime] = None


class Project(ProjectBase, table=True):
    __tablename__ = "projects"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    members: list["ProjectMember"] = Relationship(back_populates="project")
    subsections: list["ProjectSubsection"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    approvals: list["StageApproval"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None


class ProjectPublic(ProjectBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
