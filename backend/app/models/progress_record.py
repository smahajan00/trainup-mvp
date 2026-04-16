from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.metric_type import MetricType
    from app.models.session_summary import SessionSummary
    from app.models.user import User


class ProgressRecord(BaseModel):
    __tablename__ = "progress_records"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    summary_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("session_summaries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    metric_value: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    date_recorded: Mapped[date] = mapped_column(Date, nullable=False)

    user: Mapped[User] = relationship(back_populates="progress_records")
    summary: Mapped[SessionSummary] = relationship(back_populates="progress_records")
    metric_type: Mapped[MetricType] = relationship(back_populates="progress_records")

