from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.progress_record import ProgressRecord
    from app.models.training_session import TrainingSession
    from app.models.user_profile import UserProfile


class User(BaseModel):
    __tablename__ = "users"

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    profile: Mapped[UserProfile | None] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    training_sessions: Mapped[list[TrainingSession]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    progress_records: Mapped[list[ProgressRecord]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

