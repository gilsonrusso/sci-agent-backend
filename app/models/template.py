import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class TemplateBase(SQLModel):
    title: str = Field(index=True)
    description: Optional[str] = None
    content: str  # Stores LaTeX/Markdown content
    is_default: bool = Field(default=False)


class Template(TemplateBase, table=True):
    __tablename__ = "templates"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TemplateCreate(TemplateBase):
    pass


class TemplateUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    is_default: Optional[bool] = None


class TemplatePublic(TemplateBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
