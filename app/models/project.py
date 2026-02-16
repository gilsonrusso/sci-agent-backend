import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class ProjectBase(SQLModel):
    title: str = Field(index=True)
    description: Optional[str] = None
    content: Optional[str] = None  # Stores LaTeX/Markdown content


class Project(ProjectBase, table=True):
    __tablename__ = "projects"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


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
