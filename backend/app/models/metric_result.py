from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import (
    ComputationStatus,
    SeverityLevel,
    computation_status_enum,
    severity_level_enum,
)

PHASE0_FORMULA_VERSION = "phase0_v0_1_0"

if TYPE_CHECKING:
    from app.models.metric_type import MetricType
    from app.models.training_session import TrainingSession


class MetricResult(BaseModel):
    __tablename__ = "metric_results"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("training_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    phase_id: Mapped[str] = mapped_column(String(80), nullable=False)
    raw_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    ideal_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    ideal_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    deviation: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    severity_level: Mapped[SeverityLevel] = mapped_column(severity_level_enum, nullable=False)
    normalized_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    affected_body_part: Mapped[str] = mapped_column(String(120), nullable=False)
    computation_status: Mapped[ComputationStatus] = mapped_column(
        computation_status_enum,
        nullable=False,
    )
    valid_frame_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    formula_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=PHASE0_FORMULA_VERSION,
        server_default=PHASE0_FORMULA_VERSION,
    )

    session: Mapped[TrainingSession] = relationship(back_populates="metric_results")
    metric_type: Mapped[MetricType] = relationship(back_populates="metric_results")
