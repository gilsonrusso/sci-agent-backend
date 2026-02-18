import uuid
from datetime import datetime
from typing import Optional, Dict
from sqlmodel import Field, SQLModel, JSON, Column


class ProjectAuditLog(SQLModel, table=True):
    __tablename__ = "project_audit_logs"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id")
    actor_id: uuid.UUID = Field(foreign_key="users.id")
    action_type: str
    previous_value: Dict = Field(sa_column=Column(JSON), default={})
    new_value: Dict = Field(sa_column=Column(JSON), default={})
    justification: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
