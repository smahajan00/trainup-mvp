from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, JSON, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.progress_record import ProgressRecord
    from app.models.training_session import TrainingSession


class SessionSummary(BaseModel):
    __tablename__ = "session_summaries"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("training_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    overall_accuracy: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    strengths: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    weaknesses: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    recommendations: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)

    session: Mapped[TrainingSession] = relationship(back_populates="summary")
    progress_records: Mapped[list[ProgressRecord]] = relationship(
        back_populates="summary",
        cascade="all, delete-orphan",
    )

