from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from statistics import mean

from app.models.drill import Drill
from app.schemas.progress import (
    SessionRecommendations,
    SessionStrengths,
    SessionWeaknesses,
    SummaryStrengthMetric,
    SessionWeaknessIssue,
)
from app.schemas.session import DrillEvaluationResult, FeedbackResponse


def _format_label(value: str) -> str:
    return value.replace("_", " ")


def _join_labels(values: list[str]) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return f"{', '.join(values[:-1])}, and {values[-1]}"


def _normalize_focus_text(value: str) -> str:
    cleaned = value.strip().rstrip(".")
    if not cleaned:
        return "Repeat the drill with slower, more controlled execution"
    return cleaned


@dataclass
class SummaryService:
    def build_summary_payload(
        self,
        *,
        evaluation_result: DrillEvaluationResult,
        feedback_rows: list[FeedbackResponse],
        drill: Drill,
    ) -> dict[str, object]:
        metric_scores = evaluation_result.metric_scores
        average_score = mean(metric_scores.values()) if metric_scores else 0.0
        overall_accuracy = round(average_score * 100, 2)

        strengths_metrics = sorted(
            [
                SummaryStrengthMetric(name=metric_name, score=score)
                for metric_name, score in metric_scores.items()
                if score >= 0.85
            ],
            key=lambda metric: metric.score,
            reverse=True,
        )

        weaknesses_issues = [
            SessionWeaknessIssue(
                metric=issue.metric,
                severity=issue.severity_level,
                issue_label=issue.issue_label,
            )
            for issue in evaluation_result.issues
        ]

        recommendation_templates = (
            list((drill.coaching_rules or {}).get("recommendation_templates", []))
            if evaluation_result.issues
            else []
        )

        summary_text = self._build_summary_text(
            drill_name=drill.drill_name,
            strengths=strengths_metrics,
            weaknesses=weaknesses_issues,
            feedback_rows=feedback_rows,
        )

        return {
            "summary_text": summary_text,
            "overall_accuracy": Decimal(f"{overall_accuracy:.2f}"),
            "strengths": SessionStrengths(metrics=strengths_metrics).model_dump(mode="json"),
            "weaknesses": SessionWeaknesses(issues=weaknesses_issues).model_dump(mode="json"),
            "recommendations": SessionRecommendations(
                actions=recommendation_templates
            ).model_dump(mode="json"),
        }

    def _build_summary_text(
        self,
        *,
        drill_name: str,
        strengths: list[SummaryStrengthMetric],
        weaknesses: list[SessionWeaknessIssue],
        feedback_rows: list[FeedbackResponse],
    ) -> str:
        strength_labels = [_format_label(metric.name) for metric in strengths[:2]]
        issue_labels = [issue.issue_label.lower() for issue in weaknesses[:2]]

        if not weaknesses:
            strengths_text = (
                _join_labels(strength_labels)
                if strength_labels
                else "the current deterministic movement checks"
            )
            return (
                f"Your {drill_name} session stayed consistent across the current deterministic pipeline, "
                f"with strongest results in {strengths_text}. Keep repeating the same controlled movement pattern "
                "as drill-specific evaluation becomes more detailed."
            )

        focus_cues = [row.coaching_cue for row in feedback_rows[:2]]
        if focus_cues:
            focus_text = _normalize_focus_text(focus_cues[0])
        else:
            focus_text = "repeat the drill with slower, more controlled execution"

        if strength_labels:
            return (
                f"Your {drill_name} session shows solid control in {_join_labels(strength_labels)}. "
                f"However, {_join_labels(issue_labels)} need improvement. Use this cue: {focus_text}"
                "."
            )

        return (
            f"Your {drill_name} session needs more consistency in {_join_labels(issue_labels)}. "
            f"Use this cue: {focus_text}."
        )
