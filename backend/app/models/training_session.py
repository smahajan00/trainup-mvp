from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import (
    CameraView,
    DominantSide,
    InputType,
    SessionStatus,
    SkillLevel,
    camera_view_enum,
    dominant_side_enum,
    input_type_enum,
    session_status_enum,
    skill_level_enum,
)

if TYPE_CHECKING:
    from app.models.drill import Drill
    from app.models.feedback import Feedback
    from app.models.metric_result import MetricResult
    from app.models.session_artifact import SessionArtifact
    from app.models.session_summary import SessionSummary
    from app.models.user import User


class TrainingSession(BaseModel):
    __tablename__ = "training_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    drill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    input_type: Mapped[InputType] = mapped_column(input_type_enum, nullable=False)
    skill_level: Mapped[SkillLevel] = mapped_column(skill_level_enum, nullable=False)
    camera_view: Mapped[CameraView | None] = mapped_column(camera_view_enum, nullable=True)
    dominant_side: Mapped[DominantSide | None] = mapped_column(
        dominant_side_enum,
        nullable=True,
    )
    status: Mapped[SessionStatus] = mapped_column(session_status_enum, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="training_sessions")
    drill: Mapped[Drill] = relationship(back_populates="training_sessions")
    feedback_items: Mapped[list[Feedback]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    metric_results: Mapped[list[MetricResult]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    summary: Mapped[SessionSummary | None] = relationship(
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )
    artifacts: Mapped[list[SessionArtifact]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
