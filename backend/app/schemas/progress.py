from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import Field

from app.models.enums import InputType, SessionStatus, SeverityLevel
from app.schemas.base import APIBaseModel


class SummaryStrengthMetric(APIBaseModel):
    name: str
    score: float = Field(ge=0, le=1)


class SessionStrengths(APIBaseModel):
    metrics: list[SummaryStrengthMetric] = Field(default_factory=list)


class SessionWeaknessIssue(APIBaseModel):
    metric: str
    severity: SeverityLevel
    issue_label: str


class SessionWeaknesses(APIBaseModel):
    issues: list[SessionWeaknessIssue] = Field(default_factory=list)


class SessionRecommendations(APIBaseModel):
    actions: list[str] = Field(default_factory=list)


class SessionSummaryResponse(APIBaseModel):
    id: UUID
    session_id: UUID
    summary_text: str
    overall_accuracy: float = Field(ge=0, le=100)
    strengths: SessionStrengths
    weaknesses: SessionWeaknesses
    recommendations: SessionRecommendations
    created_at: datetime


class RecentProgressSessionResponse(APIBaseModel):
    session_id: UUID
    drill_name: str
    sport_name: str
    input_type: InputType
    status: SessionStatus
    start_time: datetime
    overall_accuracy: float = Field(ge=0, le=100)
    summary_text: str


class RecentMetricProgressResponse(APIBaseModel):
    progress_id: UUID
    summary_id: UUID
    session_id: UUID
    drill_name: str
    sport_name: str
    metric_name: str
    metric_unit: str
    metric_value: float = Field(ge=0)
    date_recorded: date
    created_at: datetime


class RecentProgressResponse(APIBaseModel):
    recent_sessions: list[RecentProgressSessionResponse] = Field(default_factory=list)
    recent_metrics: list[RecentMetricProgressResponse] = Field(default_factory=list)
