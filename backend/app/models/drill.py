from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import skill_level_enum, SkillLevel

if TYPE_CHECKING:
    from app.models.sport import Sport
    from app.models.training_session import TrainingSession


class Drill(BaseModel):
    __tablename__ = "drills"

    sport_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    drill_name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty_level: Mapped[SkillLevel] = mapped_column(skill_level_enum, nullable=False)
    reference_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    coaching_rules: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    target_metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    sport: Mapped[Sport] = relationship(back_populates="drills")
    training_sessions: Mapped[list[TrainingSession]] = relationship(
        back_populates="drill",
        cascade="all, delete-orphan",
    )
