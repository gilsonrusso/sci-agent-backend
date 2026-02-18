import uuid
from datetime import datetime
from sqlmodel import Session
from app.models.audit_log import ProjectAuditLog


def log_action(
    session: Session,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    action_type: str,
    previous_value: dict = {},
    new_value: dict = {},
    justification: str = None,
):
    audit_log = ProjectAuditLog(
        project_id=project_id,
        actor_id=actor_id,
        action_type=action_type,
        previous_value=previous_value,
        new_value=new_value,
        justification=justification,
        created_at=datetime.utcnow(),
    )
    session.add(audit_log)
    session.commit()
    session.refresh(audit_log)
    return audit_log
