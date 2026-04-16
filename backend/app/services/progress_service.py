from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.repositories.progress_repository import ProgressRepository
from app.repositories.session_summary_repository import SessionSummaryRepository
from app.schemas.progress import (
    RecentMetricProgressResponse,
    RecentProgressResponse,
    RecentProgressSessionResponse,
)


@dataclass
class ProgressService:
    summaries: SessionSummaryRepository
    progress_records: ProgressRepository

    def get_recent_progress(
        self,
        *,
        user_id: UUID,
        session_limit: int = 5,
        metric_limit: int = 20,
    ) -> RecentProgressResponse:
        recent_summaries = self.summaries.list_recent_for_user(user_id=user_id, limit=session_limit)
        recent_metrics = self.progress_records.list_recent_for_user(user_id=user_id, limit=metric_limit)

        return RecentProgressResponse(
            recent_sessions=[
                RecentProgressSessionResponse(
                    session_id=summary.session_id,
                    drill_name=summary.session.drill.drill_name,
                    sport_name=summary.session.drill.sport.sport_name,
                    input_type=summary.session.input_type,
                    status=summary.session.status,
                    start_time=summary.session.start_time,
                    overall_accuracy=float(summary.overall_accuracy),
                    summary_text=summary.summary_text,
                )
                for summary in recent_summaries
            ],
            recent_metrics=[
                RecentMetricProgressResponse(
                    progress_id=record.id,
                    summary_id=record.summary_id,
                    session_id=record.summary.session_id,
                    drill_name=record.summary.session.drill.drill_name,
                    sport_name=record.summary.session.drill.sport.sport_name,
                    metric_name=record.metric_type.metric_name,
                    metric_unit=record.metric_type.metric_unit,
                    metric_value=float(record.metric_value),
                    date_recorded=record.date_recorded,
                    created_at=record.created_at,
                )
                for record in recent_metrics
            ],
        )
