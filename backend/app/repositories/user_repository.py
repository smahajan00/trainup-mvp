from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        statement = (
            select(User)
            .options(selectinload(User.profile))
            .where(User.email == email)
        )
        return self.db.scalar(statement)

    def get_by_id(self, user_id: UUID) -> User | None:
        statement = (
            select(User)
            .options(selectinload(User.profile))
            .where(User.id == user_id)
        )
        return self.db.scalar(statement)

    def create(self, *, full_name: str, email: str, password_hash: str) -> User:
        user = User(
            full_name=full_name,
            email=email,
            password_hash=password_hash,
        )
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user
