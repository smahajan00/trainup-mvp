from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.engines.fuzzy_engine.fuzzy_interpretation_contract import FUZZY_BASE_LABELS
from app.engines.fuzzy_engine.it2_fuzzy_contract import (
    IT2_FUZZY_VERSION,
    IT2UncertaintyConfig,
    get_it2_uncertainty_config,
)
from app.models.enums import ComputationStatus, SkillLevel
from app.schemas.session import (
    FuzzyInterpretationResult,
    FuzzyMetricInterpretationResponse,
    IT2FuzzyInterpretationResult,
    IT2FuzzyMetricInterpretationResponse,
    IT2HighestUncertaintyMetricResponse,
    IT2MembershipIntervalResponse,
    IT2UncertaintySummaryResponse,
)

_FUZZY_LABEL_PRIORITY = {
    "IDEAL": 0,
    "SLIGHTLY_OFF": 1,
    "MODERATELY_OFF": 2,
    "STRONGLY_OFF": 3,
}


def compute_ambiguity_score(membership_scores: dict[str, float] | None) -> float:
    if not membership_scores:
        return 0.0
    ordered_scores = sorted(
        (max(0.0, min(1.0, float(score))) for score in membership_scores.values()),
        reverse=True,
    )
    if len(ordered_scores) < 2:
        return 0.0
    return round(ordered_scores[1], 4)


def compute_uncertainty_width(
    *,
    membership_scores: dict[str, float] | None,
    dominant_label_confidence: float | None,
    diagnostic_flags: list[str] | None,
    config: IT2UncertaintyConfig,
) -> float:
    confidence_uncertainty = 1.0 - float(dominant_label_confidence or 0.0)
    ambiguity_uncertainty = compute_ambiguity_score(membership_scores)
    diagnostic_uncertainty = 1.0 if diagnostic_flags else 0.0
    raw_uncertainty = (
        config.base_uncertainty
        + config.confidence_weight * confidence_uncertainty
        + config.ambiguity_weight * ambiguity_uncertainty
        + config.diagnostic_weight * diagnostic_uncertainty
    )
    bounded = max(
        config.min_uncertainty,
        min(config.max_uncertainty, raw_uncertainty),
    )
    return round(bounded, 4)


def compute_interval_memberships(
    membership_scores: dict[str, float],
    uncertainty_width: float,
) -> dict[str, IT2MembershipIntervalResponse]:
    intervals: dict[str, IT2MembershipIntervalResponse] = {}
    for label in FUZZY_BASE_LABELS:
        score = max(0.0, min(1.0, float(membership_scores.get(label, 0.0))))
        lower = max(0.0, score - uncertainty_width)
        upper = min(1.0, score + uncertainty_width)
        intervals[label] = IT2MembershipIntervalResponse(
            lower=round(lower, 4),
            upper=round(upper, 4),
            width=round(upper - lower, 4),
        )
    return intervals


def assign_primary_interval_label(
    interval_memberships: dict[str, IT2MembershipIntervalResponse],
) -> str:
    return max(
        FUZZY_BASE_LABELS,
        key=lambda label: (
            round(
                (
                    interval_memberships[label].lower
                    + interval_memberships[label].upper
                )
                / 2.0,
                4,
            ),
            interval_memberships[label].upper,
            _FUZZY_LABEL_PRIORITY[label],
        ),
    )


def assign_uncertainty_category(
    *,
    computation_status: ComputationStatus,
    uncertainty_width: float | None,
    config: IT2UncertaintyConfig,
) -> str:
    if (
        computation_status is not ComputationStatus.COMPUTED
        or uncertainty_width is None
    ):
        return "NOT_INTERPRETABLE"
    if uncertainty_width <= config.low_uncertainty_threshold:
        return "LOW_UNCERTAINTY"
    if uncertainty_width <= config.medium_uncertainty_threshold:
        return "MEDIUM_UNCERTAINTY"
    return "HIGH_UNCERTAINTY"


@dataclass(frozen=True)
class IT2FuzzyInterpretationService:
    enabled: bool = True
    config: IT2UncertaintyConfig = get_it2_uncertainty_config()

    def interpret(
        self,
        *,
        fuzzy_result: FuzzyInterpretationResult,
    ) -> IT2FuzzyInterpretationResult:
        if not self.enabled:
            return self.build_failure_result(
                session_id=fuzzy_result.session_id,
                sport_id=fuzzy_result.sport_id,
                drill_id=fuzzy_result.drill_id,
                skill_level=fuzzy_result.skill_level,
                diagnostic_flags=["IT2_FUZZY_DISABLED"],
                status="DISABLED",
            )

        if fuzzy_result.status not in {"COMPLETED", "NO_INTERPRETABLE_METRICS"}:
            return self.build_failure_result(
                session_id=fuzzy_result.session_id,
                sport_id=fuzzy_result.sport_id,
                drill_id=fuzzy_result.drill_id,
                skill_level=fuzzy_result.skill_level,
                diagnostic_flags=[
                    *fuzzy_result.diagnostic_flags,
                    "UNUSABLE_FUZZY_INTERPRETATION_RESULT",
                    f"FUZZY_STATUS:{fuzzy_result.status}",
                ],
            )

        metric_results = [
            self._interpret_metric(metric)
            for metric in fuzzy_result.fuzzy_metric_results
        ]
        summary = self._build_summary(metric_results)

        status = (
            "COMPLETED"
            if any(
                metric.uncertainty_category != "NOT_INTERPRETABLE"
                for metric in metric_results
            )
            else "NO_INTERPRETABLE_METRICS"
        )
        diagnostic_flags = self._dedupe(
            [
                *fuzzy_result.diagnostic_flags,
                *[
                    flag
                    for metric in metric_results
                    for flag in metric.diagnostic_flags
                ],
            ]
        )
        if status == "NO_INTERPRETABLE_METRICS":
            diagnostic_flags = self._dedupe(
                [*diagnostic_flags, "NO_IT2_INTERPRETABLE_METRICS"]
            )

        return IT2FuzzyInterpretationResult(
            it2_fuzzy_version=IT2_FUZZY_VERSION,
            status=status,
            session_id=fuzzy_result.session_id,
            sport_id=fuzzy_result.sport_id,
            drill_id=fuzzy_result.drill_id,
            skill_level=fuzzy_result.skill_level,
            it2_metric_results=metric_results,
            uncertainty_summary=summary,
            diagnostic_flags=diagnostic_flags,
            created_at=datetime.now(UTC),
        )

    def build_failure_result(
        self,
        *,
        session_id: UUID,
        sport_id: UUID,
        drill_id: UUID,
        skill_level: SkillLevel,
        diagnostic_flags: list[str],
        status: str = "FAILED",
    ) -> IT2FuzzyInterpretationResult:
        return IT2FuzzyInterpretationResult(
            it2_fuzzy_version=IT2_FUZZY_VERSION,
            status=status,
            session_id=session_id,
            sport_id=sport_id,
            drill_id=drill_id,
            skill_level=skill_level,
            it2_metric_results=[],
            uncertainty_summary=IT2UncertaintySummaryResponse(
                low_count=0,
                medium_count=0,
                high_count=0,
                not_interpretable_count=0,
                average_uncertainty_width=0.0,
                highest_uncertainty_metric=IT2HighestUncertaintyMetricResponse(),
                summary_text=(
                    "Interval Type-2 fuzzy interpretation could not be generated."
                ),
            ),
            diagnostic_flags=self._dedupe(diagnostic_flags),
            created_at=datetime.now(UTC),
        )

    def _interpret_metric(
        self,
        metric: FuzzyMetricInterpretationResponse,
    ) -> IT2FuzzyMetricInterpretationResponse:
        if metric.computation_status is not ComputationStatus.COMPUTED:
            return self._not_interpretable_metric(
                metric=metric,
                diagnostic_flags=["METRIC_NOT_COMPUTABLE"],
            )
        if not metric.membership_scores:
            return self._not_interpretable_metric(
                metric=metric,
                diagnostic_flags=["MISSING_MEMBERSHIP_SCORES"],
            )
        if metric.primary_fuzzy_label == "NOT_INTERPRETABLE":
            return self._not_interpretable_metric(
                metric=metric,
                diagnostic_flags=["TYPE1_NOT_INTERPRETABLE"],
            )

        uncertainty_width = compute_uncertainty_width(
            membership_scores=metric.membership_scores,
            dominant_label_confidence=metric.dominant_label_confidence,
            diagnostic_flags=metric.diagnostic_flags,
            config=self.config,
        )
        interval_memberships = compute_interval_memberships(
            metric.membership_scores,
            uncertainty_width,
        )
        return IT2FuzzyMetricInterpretationResponse(
            phase_id=metric.phase_id,
            metric_id=metric.metric_id,
            metric_name=metric.metric_name,
            computation_status=metric.computation_status,
            deviation=metric.deviation,
            issue_direction=metric.issue_direction,
            severity_level=metric.severity_level,
            affected_body_part=metric.affected_body_part,
            type1_primary_label=metric.primary_fuzzy_label,
            type1_direction_aware_label=metric.direction_aware_label,
            dominant_label_confidence=metric.dominant_label_confidence,
            uncertainty_width=uncertainty_width,
            uncertainty_category=assign_uncertainty_category(
                computation_status=metric.computation_status,
                uncertainty_width=uncertainty_width,
                config=self.config,
            ),
            interval_memberships=interval_memberships,
            primary_interval_label=assign_primary_interval_label(interval_memberships),
            diagnostic_flags=list(metric.diagnostic_flags),
        )

    def _build_summary(
        self,
        metric_results: list[IT2FuzzyMetricInterpretationResponse],
    ) -> IT2UncertaintySummaryResponse:
        low_count = sum(
            metric.uncertainty_category == "LOW_UNCERTAINTY"
            for metric in metric_results
        )
        medium_count = sum(
            metric.uncertainty_category == "MEDIUM_UNCERTAINTY"
            for metric in metric_results
        )
        high_count = sum(
            metric.uncertainty_category == "HIGH_UNCERTAINTY"
            for metric in metric_results
        )
        not_interpretable_count = sum(
            metric.uncertainty_category == "NOT_INTERPRETABLE"
            for metric in metric_results
        )
        interpretable = [
            metric
            for metric in metric_results
            if metric.uncertainty_width is not None
        ]
        average_uncertainty_width = round(
            (
                sum(metric.uncertainty_width or 0.0 for metric in interpretable)
                / len(interpretable)
            ),
            4,
        ) if interpretable else 0.0

        highest_metric = max(
            interpretable,
            key=lambda metric: (
                metric.uncertainty_width or 0.0,
                metric.phase_id,
                metric.metric_id or metric.metric_name,
            ),
            default=None,
        )
        if highest_metric is None:
            highest_uncertainty_metric = IT2HighestUncertaintyMetricResponse()
        else:
            highest_uncertainty_metric = IT2HighestUncertaintyMetricResponse(
                phase_id=highest_metric.phase_id,
                metric_id=highest_metric.metric_id,
                uncertainty_width=highest_metric.uncertainty_width,
            )

        return IT2UncertaintySummaryResponse(
            low_count=low_count,
            medium_count=medium_count,
            high_count=high_count,
            not_interpretable_count=not_interpretable_count,
            average_uncertainty_width=average_uncertainty_width,
            highest_uncertainty_metric=highest_uncertainty_metric,
            summary_text=self._build_summary_text(
                low_count=low_count,
                medium_count=medium_count,
                high_count=high_count,
                not_interpretable_count=not_interpretable_count,
                highest_metric=highest_metric,
            ),
        )

    def _build_summary_text(
        self,
        *,
        low_count: int,
        medium_count: int,
        high_count: int,
        not_interpretable_count: int,
        highest_metric: IT2FuzzyMetricInterpretationResponse | None,
    ) -> str:
        if highest_metric is None:
            if not_interpretable_count > 0:
                return (
                    "Some metrics could not be interval-interpreted due to missing or "
                    "non-computable fuzzy inputs."
                )
            return "No interval Type-2 fuzzy interpretations were available."
        if high_count > 0:
            return (
                "High uncertainty appears mainly in "
                f"{highest_metric.affected_body_part}-related metrics."
            )
        if medium_count > 0:
            return "Most interval Type-2 fuzzy interpretations show medium uncertainty."
        return "Most interval Type-2 fuzzy interpretations have low uncertainty."

    @staticmethod
    def _not_interpretable_metric(
        *,
        metric: FuzzyMetricInterpretationResponse,
        diagnostic_flags: list[str],
    ) -> IT2FuzzyMetricInterpretationResponse:
        return IT2FuzzyMetricInterpretationResponse(
            phase_id=metric.phase_id,
            metric_id=metric.metric_id,
            metric_name=metric.metric_name,
            computation_status=metric.computation_status,
            deviation=metric.deviation,
            issue_direction=metric.issue_direction,
            severity_level=metric.severity_level,
            affected_body_part=metric.affected_body_part,
            type1_primary_label=metric.primary_fuzzy_label,
            type1_direction_aware_label=metric.direction_aware_label,
            dominant_label_confidence=metric.dominant_label_confidence,
            uncertainty_width=None,
            uncertainty_category="NOT_INTERPRETABLE",
            interval_memberships={
                label: IT2MembershipIntervalResponse(
                    lower=0.0,
                    upper=0.0,
                    width=0.0,
                )
                for label in FUZZY_BASE_LABELS
            },
            primary_interval_label="NOT_INTERPRETABLE",
            diagnostic_flags=diagnostic_flags,
        )

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        deduped: list[str] = []
        for value in values:
            if value not in deduped:
                deduped.append(value)
        return deduped
