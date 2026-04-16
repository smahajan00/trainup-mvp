from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models.drill import Drill
from app.models.metric_type import MetricType
from app.models.progress_record import ProgressRecord
from app.models.session_summary import SessionSummary
from app.models.training_session import TrainingSession


class ProgressRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def delete_by_summary_id(self, *, summary_id: UUID) -> None:
        self.db.execute(delete(ProgressRecord).where(ProgressRecord.summary_id == summary_id))
        self.db.flush()

    def create(
        self,
        *,
        user_id: UUID,
        summary_id: UUID,
        metric_id: UUID,
        metric_value: Decimal,
        date_recorded: date,
    ) -> ProgressRecord:
        progress_record = ProgressRecord(
            user_id=user_id,
            summary_id=summary_id,
            metric_id=metric_id,
            metric_value=metric_value,
            date_recorded=date_recorded,
        )
        self.db.add(progress_record)
        self.db.flush()
        self.db.refresh(progress_record)
        return progress_record

    def list_recent_for_user(
        self,
        *,
        user_id: UUID,
        limit: int,
    ) -> list[ProgressRecord]:
        statement = (
            select(ProgressRecord)
            .options(
                selectinload(ProgressRecord.metric_type),
                selectinload(ProgressRecord.summary)
                .selectinload(SessionSummary.session)
                .selectinload(TrainingSession.drill)
                .selectinload(Drill.sport),
            )
            .where(ProgressRecord.user_id == user_id)
            .order_by(ProgressRecord.date_recorded.desc(), ProgressRecord.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(statement))
