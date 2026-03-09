from typing import List
from uuid import UUID
from sqlmodel import Session, select
from sqlalchemy import text
from app.models.onboarding_session import OnboardingSession


class SQLOnboardingSessionRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self, user_id: UUID, conversation_id: UUID, title: str
    ) -> OnboardingSession:
        db_obj = OnboardingSession(id=conversation_id, user_id=user_id, title=title)
        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)
        return db_obj

    def get_by_id(self, conversation_id: UUID) -> OnboardingSession | None:
        return self.session.get(OnboardingSession, conversation_id)

    def get_all_for_user(self, user_id: UUID) -> List[OnboardingSession]:
        statement = (
            select(OnboardingSession)
            .where(OnboardingSession.user_id == user_id)
            .order_by(OnboardingSession.updated_at.desc())
        )
        return self.session.exec(statement).all()

    def update_title(self, conversation_id: UUID, new_title: str):
        db_obj = self.get_by_id(conversation_id)
        if db_obj:
            db_obj.title = new_title
            self.session.add(db_obj)
            self.session.commit()

    def update_timestamp(self, conversation_id: UUID):
        import datetime

        db_obj = self.get_by_id(conversation_id)
        if db_obj:
            db_obj.updated_at = datetime.datetime.utcnow()
            self.session.add(db_obj)
            self.session.commit()

    def delete(self, conversation_id: UUID) -> bool:
        db_obj = self.get_by_id(conversation_id)
        if db_obj:
            # First, delete associated LangGraph checkpoints
            thread_id = str(conversation_id)
            try:
                self.session.execute(
                    text("DELETE FROM checkpoint_writes WHERE thread_id = :thread_id"),
                    {"thread_id": thread_id},
                )
                self.session.execute(
                    text("DELETE FROM checkpoint_blobs WHERE thread_id = :thread_id"),
                    {"thread_id": thread_id},
                )
                self.session.execute(
                    text("DELETE FROM checkpoints WHERE thread_id = :thread_id"),
                    {"thread_id": thread_id},
                )
            except Exception as e:
                # Log or handle depending on if tables exist
                print(f"Warning: Failed to delete checkpoints for {thread_id}: {e}")

            # Then delete the session metadata
            self.session.delete(db_obj)
            self.session.commit()
            return True
        return False
