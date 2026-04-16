from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import skill_level_enum, SkillLevel

if TYPE_CHECKING:
    from app.models.sport import Sport
    from app.models.user import User


class UserProfile(BaseModel):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    sport_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sports.id", ondelete="RESTRICT"),
        nullable=False,
    )
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    skill_level: Mapped[SkillLevel] = mapped_column(skill_level_enum, nullable=False)
    injury_notes: Mapped[str | None] = mapped_column(nullable=True)

    user: Mapped[User] = relationship(back_populates="profile")
    sport: Mapped[Sport] = relationship(back_populates="user_profiles")

