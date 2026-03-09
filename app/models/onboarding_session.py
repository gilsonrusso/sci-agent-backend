from uuid import UUID, uuid4
from datetime import datetime
from sqlmodel import Field, SQLModel
from sqlalchemy import Column, DateTime
from typing import Optional


class OnboardingSession(SQLModel, table=True):
    """
    Header model for Onboarding Conversations.
    Stores metadata so the Sidebar can list past chats quickly without digging into LangGraph binary blobs.
    """

    __tablename__ = "onboarding_session"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(index=True)
    title: str = Field(default="Nova Conversa", max_length=255)

    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
