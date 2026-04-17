from __future__ import annotations

from typing import Any

from app.models.enums import SeverityLevel
from app.schemas.session import DrillEvaluationResult, EvaluationIssueResponse


def classify_severity_level(
    *,
    deviation: float,
    thresholds: dict[str, float],
    severity_weight: float,
) -> SeverityLevel:
    """
    Convert rule deviation into a severity band.

    The seeded thresholds are applied against a weighted deviation score so the
    same metric miss can escalate differently for high-importance checks.
    """
    weighted_deviation = deviation * (2.0 + (severity_weight * 3.0))
    severe_threshold = float(thresholds.get("severe", 0.45))
    moderate_threshold = float(thresholds.get("moderate", 0.30))
    minor_threshold = float(thresholds.get("minor", 0.15))

    if weighted_deviation >= severe_threshold:
        return SeverityLevel.SEVERE
    if weighted_deviation >= moderate_threshold:
        return SeverityLevel.MODERATE
    if weighted_deviation >= minor_threshold:
        return SeverityLevel.MINOR
    return SeverityLevel.MINOR


def evaluate_rule_checks(
    *,
    metric_scores: dict[str, float],
    coaching_rules: dict[str, Any],
) -> list[EvaluationIssueResponse]:
    thresholds = coaching_rules.get(
        "thresholds",
        {"minor": 0.15, "moderate": 0.30, "severe": 0.45},
    )
    issues: list[EvaluationIssueResponse] = []

    for rule_check in coaching_rules.get("rule_checks", []):
        metric_name = str(rule_check.get("metric", "")).strip()
        if not metric_name or metric_name not in metric_scores:
            continue

        actual_score = metric_scores[metric_name]
        expected_min = rule_check.get("expected_min")
        expected_max = rule_check.get("expected_max")
        condition = str(rule_check.get("condition", "below_threshold"))
        deviation = 0.0
        triggered = False

        if condition == "below_threshold" and expected_min is not None:
            deviation = max(float(expected_min) - actual_score, 0.0)
            triggered = deviation > 0
        elif condition == "above_threshold" and expected_max is not None:
            deviation = max(actual_score - float(expected_max), 0.0)
            triggered = deviation > 0
        elif expected_min is not None and actual_score < float(expected_min):
            deviation = float(expected_min) - actual_score
            triggered = True
        elif expected_max is not None and actual_score > float(expected_max):
            deviation = actual_score - float(expected_max)
            triggered = True

        if not triggered:
            continue

        severity_level = classify_severity_level(
            deviation=deviation,
            thresholds=thresholds,
            severity_weight=float(rule_check.get("severity_weight", 0.5)),
        )
        issues.append(
            EvaluationIssueResponse(
                metric=metric_name,
                actual_score=round(actual_score, 3),
                expected_min=float(expected_min) if expected_min is not None else None,
                expected_max=float(expected_max) if expected_max is not None else None,
                deviation=round(deviation, 3),
                severity_level=severity_level,
                issue_label=str(rule_check.get("issue_label", metric_name)),
                coaching_cue=str(rule_check.get("coaching_cue", "")),
            )
        )

    return issues


def build_evaluation_summary_flags(
    *,
    evaluation_result: DrillEvaluationResult,
) -> list[str]:
    flags = [
        "Review complete.",
        "Scores are based on this video.",
    ]

    if not evaluation_result.issues:
        flags.append("No clear issues were flagged.")
        return flags

    highest_severity = max(
        evaluation_result.issues,
        key=lambda issue: {
            SeverityLevel.MINOR: 1,
            SeverityLevel.MODERATE: 2,
            SeverityLevel.SEVERE: 3,
        }[issue.severity_level],
    ).severity_level
    flags.append(
        f"{len(evaluation_result.issues)} issue(s) found. Highest severity: {highest_severity.value.title()}."
    )
    return flags
