from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from app.domain.workflow.types import Role


class AdvanceStageRequest(BaseModel):
    user_id: UUID
    user_role: Role


class RevertStageRequest(BaseModel):
    user_id: UUID
    user_role: Role
    target_stage: str
    reason: Optional[str] = None
