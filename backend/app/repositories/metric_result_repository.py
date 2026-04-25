from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.enums import ComputationStatus, SeverityLevel
from app.models.metric_result import MetricResult


class MetricResultRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_session_id(self, *, session_id: UUID) -> list[MetricResult]:
        statement = (
            select(MetricResult)
            .where(MetricResult.session_id == session_id)
            .order_by(MetricResult.created_at.asc(), MetricResult.id.asc())
        )
        return list(self.db.scalars(statement))

    def delete_by_session_id(self, *, session_id: UUID) -> None:
        self.db.execute(delete(MetricResult).where(MetricResult.session_id == session_id))
        self.db.flush()

    def create(
        self,
        *,
        session_id: UUID,
        metric_id: UUID,
        phase_id: str,
        raw_value: Decimal | None,
        unit: str,
        ideal_min: Decimal | None,
        ideal_max: Decimal | None,
        deviation: Decimal | None,
        severity_level: SeverityLevel,
        normalized_score: Decimal | None,
        affected_body_part: str,
        computation_status: ComputationStatus,
        valid_frame_count: int,
        formula_version: str,
    ) -> MetricResult:
        metric_result = MetricResult(
            session_id=session_id,
            metric_id=metric_id,
            phase_id=phase_id,
            raw_value=raw_value,
            unit=unit,
            ideal_min=ideal_min,
            ideal_max=ideal_max,
            deviation=deviation,
            severity_level=severity_level,
            normalized_score=normalized_score,
            affected_body_part=affected_body_part,
            computation_status=computation_status,
            valid_frame_count=valid_frame_count,
            formula_version=formula_version,
        )
        self.db.add(metric_result)
        self.db.flush()
        self.db.refresh(metric_result)
        return metric_result
