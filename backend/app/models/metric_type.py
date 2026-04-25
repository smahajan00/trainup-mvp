from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.metric_result import MetricResult
    from app.models.progress_record import ProgressRecord


class MetricType(BaseModel):
    __tablename__ = "metric_types"

    metric_name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    metric_unit: Mapped[str] = mapped_column(String(50), nullable=False)

    metric_results: Mapped[list[MetricResult]] = relationship(
        back_populates="metric_type"
    )
    progress_records: Mapped[list[ProgressRecord]] = relationship(back_populates="metric_type")
