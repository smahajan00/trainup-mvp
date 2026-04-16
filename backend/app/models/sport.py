from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.drill import Drill
    from app.models.user_profile import UserProfile


class Sport(BaseModel):
    __tablename__ = "sports"

    sport_name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)

    drills: Mapped[list[Drill]] = relationship(
        back_populates="sport",
        cascade="all, delete-orphan",
    )
    user_profiles: Mapped[list[UserProfile]] = relationship(back_populates="sport")

