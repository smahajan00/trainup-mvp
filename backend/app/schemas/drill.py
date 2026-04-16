from __future__ import annotations

from uuid import UUID

from app.models.enums import SkillLevel
from app.schemas.base import APIBaseModel


class DrillTargetMetricsResponse(APIBaseModel):
    metrics: list[str]


class DrillReferenceRangeResponse(APIBaseModel):
    min: float
    max: float


class DrillReferencePayloadResponse(APIBaseModel):
    movement_type: str
    phases: list[str]
    tracked_joints: list[str]
    ideal_ranges: dict[str, DrillReferenceRangeResponse]
    stability_expectations: dict[str, float]
    notes: str


class DrillRuleCheckResponse(APIBaseModel):
    metric: str
    condition: str
    expected_min: float | None = None
    expected_max: float | None = None
    severity_weight: float
    issue_label: str
    coaching_cue: str


class DrillCoachingRulesResponse(APIBaseModel):
    primary_focus: list[str]
    thresholds: dict[str, float]
    rule_checks: list[DrillRuleCheckResponse]
    positive_cues: list[str]
    recommendation_templates: list[str]


class DrillListItemResponse(APIBaseModel):
    id: UUID
    sport_id: UUID
    drill_name: str
    description: str | None
    difficulty_level: SkillLevel
    target_metrics: DrillTargetMetricsResponse


class DrillDetailResponse(APIBaseModel):
    id: UUID
    sport_id: UUID
    sport_name: str
    drill_name: str
    description: str | None
    difficulty_level: SkillLevel
    target_metrics: DrillTargetMetricsResponse
    reference_payload: DrillReferencePayloadResponse
    coaching_rules: DrillCoachingRulesResponse
