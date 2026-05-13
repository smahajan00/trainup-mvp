from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.repositories.progress_repository import ProgressRepository
from app.repositories.session_summary_repository import SessionSummaryRepository
from app.schemas.progress import (
    ProgressRange,
    RecentMetricProgressResponse,
    RecentProgressResponse,
    RecentProgressSessionResponse,
)

logger = logging.getLogger("uvicorn.error")


def _range_cutoff(selected_range: ProgressRange) -> datetime | None:
    now = datetime.now(UTC)
    if selected_range == "weekly":
        return now - timedelta(days=7)
    if selected_range == "monthly":
        return now - timedelta(days=30)
    return None


def _trend_label(delta: float | None) -> str:
    if delta is None:
        return "Need data"
    if abs(delta) < 1:
        return "Stable"
    return "Improving" if delta > 0 else "Needs attention"


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
        progress_range: ProgressRange | None = None,
    ) -> RecentProgressResponse:
        selected_range: ProgressRange = progress_range or "all_time"
        cutoff = _range_cutoff(selected_range)
        recent_summaries = self.summaries.list_recent_for_user(
            user_id=user_id,
            limit=session_limit,
            since=cutoff,
        )
        recent_metrics = self.progress_records.list_recent_for_user(
            user_id=user_id,
            limit=metric_limit,
            since=cutoff,
        )
        total_analyzed_sessions, average_score, best_score = (
            self.summaries.get_score_aggregate_for_user(user_id=user_id, since=cutoff)
        )
        trend_summaries = self.summaries.list_recent_for_user(
            user_id=user_id,
            limit=2,
            since=cutoff,
        )
        trend_delta = (
            float(trend_summaries[0].overall_accuracy)
            - float(trend_summaries[1].overall_accuracy)
            if len(trend_summaries) >= 2
            else None
        )
        logger.info(
            "Progress dashboard query returned %s sessions",
            total_analyzed_sessions,
            extra={
                "selected_range": selected_range,
                "session_count": total_analyzed_sessions,
                "recent_session_count": len(recent_summaries),
                "metric_count": len(recent_metrics),
            },
        )

        return RecentProgressResponse(
            selected_range=selected_range,
            total_analyzed_sessions=total_analyzed_sessions,
            average_score=average_score,
            best_score=best_score,
            trend_delta=trend_delta,
            trend_label=_trend_label(trend_delta),
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
