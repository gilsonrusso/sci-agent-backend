import datetime
from typing import List, Optional
from uuid import UUID
from sqlmodel import Session, select
from sqlalchemy import text
from app.models.onboarding_session import OnboardingSession


def create_onboarding_session(
    session: Session, user_id: UUID, conversation_id: UUID, title: str
) -> OnboardingSession:
    db_obj = OnboardingSession(id=conversation_id, user_id=user_id, title=title)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_onboarding_session(
    session: Session, conversation_id: UUID
) -> Optional[OnboardingSession]:
    return session.get(OnboardingSession, conversation_id)


def get_all_sessions_for_user(
    session: Session, user_id: UUID
) -> List[OnboardingSession]:
    statement = (
        select(OnboardingSession)
        .where(OnboardingSession.user_id == user_id)
        .order_by(OnboardingSession.updated_at.desc())
    )
    return session.exec(statement).all()


def update_onboarding_session_title(
    session: Session, conversation_id: UUID, new_title: str
):
    db_obj = get_onboarding_session(session, conversation_id)
    if db_obj:
        db_obj.title = new_title
        session.add(db_obj)
        session.commit()


def update_onboarding_session_timestamp(session: Session, conversation_id: UUID):
    db_obj = get_onboarding_session(session, conversation_id)
    if db_obj:
        db_obj.updated_at = datetime.datetime.utcnow()
        session.add(db_obj)
        session.commit()


def delete_onboarding_session(session: Session, conversation_id: UUID) -> bool:
    db_obj = get_onboarding_session(session, conversation_id)
    if db_obj:
        thread_id = str(conversation_id)
        try:
            session.execute(
                text("DELETE FROM checkpoint_writes WHERE thread_id = :thread_id"),
                {"thread_id": thread_id},
            )
            session.execute(
                text("DELETE FROM checkpoint_blobs WHERE thread_id = :thread_id"),
                {"thread_id": thread_id},
            )
            session.execute(
                text("DELETE FROM checkpoints WHERE thread_id = :thread_id"),
                {"thread_id": thread_id},
            )
        except Exception as e:
            print(f"Warning: Failed to delete checkpoints for {thread_id}: {e}")

        session.delete(db_obj)
        session.commit()
        return True
    return False
