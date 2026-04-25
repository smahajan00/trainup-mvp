from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models.drill import Drill
from app.models.session_summary import SessionSummary
from app.models.training_session import TrainingSession


class SessionSummaryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_session_id(self, *, session_id: UUID) -> SessionSummary | None:
        statement = (
            select(SessionSummary)
            .options(
                selectinload(SessionSummary.session)
                .selectinload(TrainingSession.drill)
                .selectinload(Drill.sport),
                selectinload(SessionSummary.progress_records),
            )
            .where(SessionSummary.session_id == session_id)
        )
        return self.db.scalar(statement)

    def upsert(
        self,
        *,
        session_id: UUID,
        summary_text: str,
        overall_accuracy: Decimal,
        strengths: dict[str, object],
        weaknesses: dict[str, object],
        recommendations: dict[str, object],
    ) -> SessionSummary:
        summary = self.get_by_session_id(session_id=session_id)

        if summary is None:
            summary = SessionSummary(
                session_id=session_id,
                summary_text=summary_text,
                overall_accuracy=overall_accuracy,
                strengths=strengths,
                weaknesses=weaknesses,
                recommendations=recommendations,
            )
            self.db.add(summary)
        else:
            summary.summary_text = summary_text
            summary.overall_accuracy = overall_accuracy
            summary.strengths = strengths
            summary.weaknesses = weaknesses
            summary.recommendations = recommendations

        self.db.flush()
        self.db.refresh(summary)
        return self.get_by_session_id(session_id=session_id) or summary

    def list_recent_for_user(
        self,
        *,
        user_id: UUID,
        limit: int,
    ) -> list[SessionSummary]:
        statement = (
            select(SessionSummary)
            .join(SessionSummary.session)
            .options(
                selectinload(SessionSummary.session)
                .selectinload(TrainingSession.drill)
                .selectinload(Drill.sport),
            )
            .where(TrainingSession.user_id == user_id)
            .order_by(TrainingSession.start_time.desc(), SessionSummary.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(statement))

    def delete_by_session_id(self, *, session_id: UUID) -> None:
        self.db.execute(
            delete(SessionSummary).where(SessionSummary.session_id == session_id)
        )
        self.db.flush()
