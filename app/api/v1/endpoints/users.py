from typing import Any
from fastapi import APIRouter
from sqlmodel import select

from app.api.deps import SessionDep, CurrentUser
from app.models.user import User, UserPublic

router = APIRouter()


@router.get("/", response_model=list[UserPublic])
def read_users(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve users.
    """
    statement = select(User).offset(skip).limit(limit)
    users = session.exec(statement).all()
    return users
