from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import SeverityLevel, severity_level_enum

if TYPE_CHECKING:
    from app.models.training_session import TrainingSession


class Feedback(BaseModel):
    __tablename__ = "feedback"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("training_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    severity_level: Mapped[SeverityLevel] = mapped_column(severity_level_enum, nullable=False)
    technique_issue: Mapped[str] = mapped_column(Text, nullable=False)
    coaching_cue: Mapped[str] = mapped_column(Text, nullable=False)
    metric_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    session: Mapped[TrainingSession] = relationship(back_populates="feedback_items")

