from enum import Enum
from uuid import UUID
import uuid
from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .user import User
    from .project import Project


class ProjectRole(str, Enum):
    OWNER = "OWNER"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"


class ProjectMember(SQLModel, table=True):
    __tablename__ = "project_members"

    project_id: uuid.UUID = Field(foreign_key="projects.id", primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    role: ProjectRole = Field(default=ProjectRole.VIEWER)

    project: "Project" = Relationship(back_populates="members")
    user: "User" = Relationship(back_populates="project_memberships")


class ProjectMemberCreate(SQLModel):
    email: str
    role: ProjectRole = ProjectRole.VIEWER


class ProjectMemberPublic(SQLModel):
    project_id: UUID
    user_id: uuid.UUID
    role: ProjectRole
    user_email: str
    user_full_name: Optional[str] = None
