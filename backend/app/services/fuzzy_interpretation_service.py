from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.engines.fuzzy_engine.fuzzy_interpretation_contract import (
    FUZZY_BASE_LABELS,
    FUZZY_INTERPRETATION_VERSION,
    FuzzyDeviationBands,
    get_fuzzy_deviation_bands,
)
from app.models.enums import ComputationStatus
from app.schemas.session import (
    DeterministicEvaluationResult,
    FuzzyInterpretationResult,
    FuzzyMetricInterpretationResponse,
    FuzzySummaryResponse,
    IssueDirection,
    MetricEvaluationResultResponse,
)

_FUZZY_LABEL_PRIORITY = {
    "IDEAL": 0,
    "SLIGHTLY_OFF": 1,
    "MODERATELY_OFF": 2,
    "STRONGLY_OFF": 3,
}


def compute_fuzzy_membership_scores(
    deviation: float,
    bands: FuzzyDeviationBands,
) -> dict[str, float]:
    bands.validate()
    deviation = max(float(deviation), 0.0)
    scores = {
        "IDEAL": _left_shoulder(
            deviation,
            start=bands.ideal_max,
            end=bands.slight_peak,
        ),
        "SLIGHTLY_OFF": _triangle(
            deviation,
            left=bands.ideal_max,
            peak=bands.slight_peak,
            right=bands.moderate_peak,
        ),
        "MODERATELY_OFF": _triangle(
            deviation,
            left=bands.slight_peak,
            peak=bands.moderate_peak,
            right=bands.strong_min,
        ),
        "STRONGLY_OFF": _right_shoulder(
            deviation,
            start=bands.moderate_peak,
            end=bands.strong_min,
        ),
    }
    return {label: round(scores[label], 4) for label in FUZZY_BASE_LABELS}


def assign_primary_fuzzy_label(membership_scores: dict[str, float]) -> str:
    return max(
        FUZZY_BASE_LABELS,
        key=lambda label: (
            membership_scores.get(label, 0.0),
            _FUZZY_LABEL_PRIORITY[label],
        ),
    )


def compute_dominant_confidence(
    membership_scores: dict[str, float] | None,
) -> float | None:
    if not membership_scores:
        return None
    return round(max(float(score) for score in membership_scores.values()), 4)


def direction_aware_fuzzy_label(
    *,
    primary_label: str,
    issue_direction: IssueDirection,
) -> str:
    if primary_label == "IDEAL" or issue_direction == "NONE":
        return "IDEAL"
    if issue_direction == "UNDER_RANGE":
        return primary_label.replace("_OFF", "_LOW")
    if issue_direction == "OVER_RANGE":
        return primary_label.replace("_OFF", "_HIGH")
    return primary_label


@dataclass(frozen=True)
class FuzzyInterpretationService:
    enabled: bool = True

    def interpret(
        self,
        *,
        evaluation_result: DeterministicEvaluationResult,
    ) -> FuzzyInterpretationResult:
        if not self.enabled:
            return self._failure_result(
                evaluation_result=evaluation_result,
                status="DISABLED",
                diagnostic_flags=["FUZZY_INTERPRETATION_DISABLED"],
            )

        if evaluation_result.status != "COMPLETED":
            return self._failure_result(
                evaluation_result=evaluation_result,
                diagnostic_flags=[
                    *evaluation_result.diagnostic_flags,
                    "EVALUATION_NOT_COMPLETED",
                    f"EVALUATION_STATUS:{evaluation_result.status}",
                ],
            )

        fuzzy_metric_results: list[FuzzyMetricInterpretationResponse] = []
        diagnostic_flags = list(evaluation_result.diagnostic_flags)
        for phase in evaluation_result.phase_results:
            for metric_result in phase.metric_results:
                fuzzy_metric = self._interpret_metric(metric_result)
                fuzzy_metric_results.append(fuzzy_metric)
                diagnostic_flags.extend(fuzzy_metric.diagnostic_flags)

        summary = self._build_summary(fuzzy_metric_results)
        if summary.interpretable_metric_count == 0:
            diagnostic_flags.append("NO_INTERPRETABLE_METRICS")

        return FuzzyInterpretationResult(
            fuzzy_version=FUZZY_INTERPRETATION_VERSION,
            status=(
                "COMPLETED"
                if summary.interpretable_metric_count > 0
                else "NO_INTERPRETABLE_METRICS"
            ),
            session_id=evaluation_result.session_id,
            drill_id=evaluation_result.drill_id,
            sport_id=evaluation_result.sport_id,
            skill_level=evaluation_result.skill_level,
            fuzzy_metric_results=fuzzy_metric_results,
            fuzzy_summary=summary,
            diagnostic_flags=self._dedupe(diagnostic_flags),
            created_at=datetime.now(UTC),
        )

    def _interpret_metric(
        self,
        metric_result: MetricEvaluationResultResponse,
    ) -> FuzzyMetricInterpretationResponse:
        if (
            metric_result.computation_status is not ComputationStatus.COMPUTED
            or metric_result.deviation is None
        ):
            return FuzzyMetricInterpretationResponse(
                metric_id=metric_result.metric_id,
                metric_name=metric_result.metric_name,
                phase_id=metric_result.phase_id,
                computation_status=metric_result.computation_status,
                deviation=metric_result.deviation,
                issue_direction=metric_result.issue_direction,
                severity_level=metric_result.severity_level,
                affected_body_part=metric_result.affected_body_part,
                primary_fuzzy_label="NOT_INTERPRETABLE",
                membership_scores={label: 0.0 for label in FUZZY_BASE_LABELS},
                dominant_label_confidence=None,
                direction_aware_label="NOT_INTERPRETABLE",
                diagnostic_flags=["METRIC_NOT_COMPUTABLE"],
            )

        try:
            bands = get_fuzzy_deviation_bands(metric_result.metric_id)
            membership_scores = compute_fuzzy_membership_scores(
                metric_result.deviation,
                bands,
            )
        except ValueError as exc:
            return FuzzyMetricInterpretationResponse(
                metric_id=metric_result.metric_id,
                metric_name=metric_result.metric_name,
                phase_id=metric_result.phase_id,
                computation_status=metric_result.computation_status,
                deviation=metric_result.deviation,
                issue_direction=metric_result.issue_direction,
                severity_level=metric_result.severity_level,
                affected_body_part=metric_result.affected_body_part,
                primary_fuzzy_label="NOT_INTERPRETABLE",
                membership_scores={label: 0.0 for label in FUZZY_BASE_LABELS},
                dominant_label_confidence=None,
                direction_aware_label="NOT_INTERPRETABLE",
                diagnostic_flags=[
                    "FUZZY_CONFIG_ERROR",
                    str(exc),
                ],
            )

        dominant_label_confidence = compute_dominant_confidence(membership_scores)
        if dominant_label_confidence is None:
            return FuzzyMetricInterpretationResponse(
                metric_id=metric_result.metric_id,
                metric_name=metric_result.metric_name,
                phase_id=metric_result.phase_id,
                computation_status=metric_result.computation_status,
                deviation=metric_result.deviation,
                issue_direction=metric_result.issue_direction,
                severity_level=metric_result.severity_level,
                affected_body_part=metric_result.affected_body_part,
                primary_fuzzy_label="NOT_INTERPRETABLE",
                membership_scores={label: 0.0 for label in FUZZY_BASE_LABELS},
                dominant_label_confidence=None,
                direction_aware_label="NOT_INTERPRETABLE",
                diagnostic_flags=["MISSING_MEMBERSHIP_SCORES"],
            )

        primary_label = assign_primary_fuzzy_label(membership_scores)
        return FuzzyMetricInterpretationResponse(
            metric_id=metric_result.metric_id,
            metric_name=metric_result.metric_name,
            phase_id=metric_result.phase_id,
            computation_status=metric_result.computation_status,
            deviation=metric_result.deviation,
            issue_direction=metric_result.issue_direction,
            severity_level=metric_result.severity_level,
            affected_body_part=metric_result.affected_body_part,
            primary_fuzzy_label=primary_label,
            membership_scores=membership_scores,
            dominant_label_confidence=dominant_label_confidence,
            direction_aware_label=direction_aware_fuzzy_label(
                primary_label=primary_label,
                issue_direction=metric_result.issue_direction,
            ),
            diagnostic_flags=[],
        )

    @staticmethod
    def _build_summary(
        fuzzy_metric_results: list[FuzzyMetricInterpretationResponse],
    ) -> FuzzySummaryResponse:
        counts = {
            "IDEAL": 0,
            "SLIGHTLY_OFF": 0,
            "MODERATELY_OFF": 0,
            "STRONGLY_OFF": 0,
            "NOT_INTERPRETABLE": 0,
        }
        concern_weights: dict[str, int] = {}
        for metric in fuzzy_metric_results:
            counts[metric.primary_fuzzy_label] += 1
            if metric.primary_fuzzy_label in {"MODERATELY_OFF", "STRONGLY_OFF"}:
                concern_weights[metric.affected_body_part] = (
                    concern_weights.get(metric.affected_body_part, 0)
                    + _FUZZY_LABEL_PRIORITY[metric.primary_fuzzy_label]
                )

        concern_labels = ("STRONGLY_OFF", "MODERATELY_OFF", "SLIGHTLY_OFF")
        dominant = next(
            (
                label
                for label in concern_labels
                if counts[label] == max(counts[item] for item in concern_labels)
                and counts[label] > 0
            ),
            "IDEAL" if counts["IDEAL"] > 0 else "NOT_INTERPRETABLE",
        )
        top_concern_areas = [
            area
            for area, _ in sorted(
                concern_weights.items(),
                key=lambda item: (-item[1], item[0]),
            )[:3]
        ]
        return FuzzySummaryResponse(
            ideal_count=counts["IDEAL"],
            slightly_off_count=counts["SLIGHTLY_OFF"],
            moderately_off_count=counts["MODERATELY_OFF"],
            strongly_off_count=counts["STRONGLY_OFF"],
            not_interpretable_count=counts["NOT_INTERPRETABLE"],
            interpretable_metric_count=sum(
                counts[label] for label in FUZZY_BASE_LABELS
            ),
            dominant_fuzzy_label=dominant,
            top_concern_areas=top_concern_areas,
        )

    @staticmethod
    def _failure_result(
        *,
        evaluation_result: DeterministicEvaluationResult,
        diagnostic_flags: list[str],
        status: str = "FAILED",
    ) -> FuzzyInterpretationResult:
        return FuzzyInterpretationResult(
            fuzzy_version=FUZZY_INTERPRETATION_VERSION,
            status=status,
            session_id=evaluation_result.session_id,
            drill_id=evaluation_result.drill_id,
            sport_id=evaluation_result.sport_id,
            skill_level=evaluation_result.skill_level,
            fuzzy_metric_results=[],
            fuzzy_summary=FuzzySummaryResponse(
                ideal_count=0,
                slightly_off_count=0,
                moderately_off_count=0,
                strongly_off_count=0,
                not_interpretable_count=0,
                interpretable_metric_count=0,
                dominant_fuzzy_label="NOT_INTERPRETABLE",
                top_concern_areas=[],
            ),
            diagnostic_flags=diagnostic_flags,
            created_at=datetime.now(UTC),
        )

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        deduped: list[str] = []
        for value in values:
            if value not in deduped:
                deduped.append(value)
        return deduped


def _left_shoulder(value: float, *, start: float, end: float) -> float:
    if value <= start:
        return 1.0
    if value >= end:
        return 0.0
    return (end - value) / (end - start)


def _right_shoulder(value: float, *, start: float, end: float) -> float:
    if value <= start:
        return 0.0
    if value >= end:
        return 1.0
    return (value - start) / (end - start)


def _triangle(value: float, *, left: float, peak: float, right: float) -> float:
    if value <= left or value >= right:
        return 0.0
    if value == peak:
        return 1.0
    if value < peak:
        return (value - left) / (peak - left)
    return (right - value) / (right - peak)
