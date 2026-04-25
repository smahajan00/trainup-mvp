from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.models.enums import ComputationStatus, SeverityLevel
from app.schemas.session import (
    DeterministicEvaluationIssueResponse,
    DeterministicEvaluationResult,
    DeterministicFeedbackItemResponse,
    DeterministicFeedbackResult,
    FEEDBACK_VERSION,
    IssueDirection,
)


_SEVERITY_PRIORITY = {
    SeverityLevel.SEVERE: 3,
    SeverityLevel.MODERATE: 2,
    SeverityLevel.MINOR: 1,
}


@dataclass(frozen=True)
class FeedbackTemplate:
    issue_title: str
    coaching_cue: str
    improvement_suggestion: str


FeedbackTemplateKey = tuple[str, IssueDirection, SeverityLevel | None, str | None]


def _template(
    metric_id: str,
    issue_direction: IssueDirection,
    issue_title: str,
    coaching_cue: str,
    improvement_suggestion: str,
    *,
    severity_level: SeverityLevel | None = None,
    phase_id: str | None = None,
) -> tuple[FeedbackTemplateKey, FeedbackTemplate]:
    return (
        (metric_id, issue_direction, severity_level, phase_id),
        FeedbackTemplate(
            issue_title=issue_title,
            coaching_cue=coaching_cue,
            improvement_suggestion=improvement_suggestion,
        ),
    )


FEEDBACK_TEMPLATE_REGISTRY: dict[FeedbackTemplateKey, FeedbackTemplate] = dict(
    [
        _template(
            "posture_accuracy",
            "UNDER_RANGE",
            "Posture needs more control",
            "Keep your chest steady and your body stacked.",
            "Slow the setup and keep your ribs over your hips.",
        ),
        _template(
            "knee_alignment_score",
            "UNDER_RANGE",
            "Knees are drifting out of line",
            "Keep your knees tracking over your toes.",
            "Move slower and press the knees outward through the rep.",
        ),
        _template(
            "torso_alignment",
            "UNDER_RANGE",
            "Torso position is unstable",
            "Keep your chest more upright and controlled.",
            "Brace before moving and avoid leaning past your base.",
        ),
        _template(
            "hip_stability",
            "UNDER_RANGE",
            "Hips are shifting",
            "Keep your hips centered between both feet.",
            "Practice the phase slowly and hold even pressure through both legs.",
        ),
        _template(
            "repetition_consistency",
            "UNDER_RANGE",
            "Reps are inconsistent",
            "Use the same depth and tempo each rep.",
            "Repeat the drill at a slower pace until the motion looks repeatable.",
        ),
        _template(
            "balance_stability",
            "UNDER_RANGE",
            "Balance is unstable",
            "Stay centered and avoid drifting side to side.",
            "Pause briefly in the key position before continuing the movement.",
        ),
        _template(
            "elbow_angle_consistency",
            "UNDER_RANGE",
            "Elbow path is inconsistent",
            "Keep your elbow in the same slot each rep.",
            "Rehearse the movement slowly and finish through the same line.",
        ),
        _template(
            "shooting_alignment",
            "UNDER_RANGE",
            "Shot line is drifting",
            "Release straight through the target line.",
            "Pause at the set point and align the elbow before extending.",
        ),
        _template(
            "shoulder_control",
            "UNDER_RANGE",
            "Shoulder control needs work",
            "Keep your shoulders quiet through the movement.",
            "Start from a stable base and avoid opening the shoulder early.",
        ),
        _template(
            "elbow_extension",
            "UNDER_RANGE",
            "Elbow extension is incomplete",
            "Extend your arm fully for a cleaner finish.",
            "Finish each rep with a controlled full extension.",
        ),
        _template(
            "wrist_elbow_alignment",
            "UNDER_RANGE",
            "Wrist and elbow are not stacked",
            "Keep your wrist over your elbow.",
            "Use a slower press and keep the hand path vertical.",
        ),
        _template(
            "lockout_control",
            "UNDER_RANGE",
            "Lockout is unstable",
            "Finish the rep with control at the top.",
            "Pause at lockout and keep the weight from drifting.",
        ),
        _template(
            "shoulder_symmetry",
            "UNDER_RANGE",
            "Shoulders are not moving evenly",
            "Keep both shoulders level and controlled.",
            "Lower the load or speed until both sides move together.",
        ),
        _template(
            "stance_width_control",
            "UNDER_RANGE",
            "Stance width is changing",
            "Keep your feet at a steady athletic width.",
            "Reset your base before holding or moving in stance.",
        ),
        _template(
            "knee_flexion",
            "UNDER_RANGE",
            "Knee bend needs adjustment",
            "Lower your hips slightly more for stability.",
            "Hold the loaded position and keep your knees bent over your feet.",
        ),
        _template(
            "hip_level_stability",
            "UNDER_RANGE",
            "Hip height is unstable",
            "Keep your hips low and level.",
            "Shorten the hold and rebuild the same hip height each rep.",
        ),
        _template(
            "plant_foot_alignment_ratio",
            "UNDER_RANGE",
            "Plant foot is inconsistent",
            "Set your support foot beside the ball.",
            "Slow the approach and place the plant foot before swinging.",
        ),
        _template(
            "instep_backswing_knee_angle",
            "UNDER_RANGE",
            "Backswing shape needs work",
            "Let the kicking knee fold before the strike.",
            "Use a shorter approach and build a smooth backswing.",
        ),
        _template(
            "instep_contact_extension",
            "UNDER_RANGE",
            "Contact leg is not extending",
            "Strike through the ball with a firm leg.",
            "Practice clean contact with a slower swing first.",
        ),
        _template(
            "instep_torso_tilt",
            "UNDER_RANGE",
            "Torso is leaning away",
            "Keep your chest over the plant leg.",
            "Finish toward the target without falling away.",
        ),
        _template(
            "instep_follow_through_stability",
            "UNDER_RANGE",
            "Follow-through is unstable",
            "Finish with a controlled follow-through.",
            "Guide the kicking leg through the target line after contact.",
        ),
        _template(
            "support_foot_distance_ratio",
            "UNDER_RANGE",
            "Support foot distance is inconsistent",
            "Place your support foot beside the ball.",
            "Rehearse the final step so the plant foot lands at the same distance.",
        ),
        _template(
            "shooting_knee_load",
            "UNDER_RANGE",
            "Kicking leg load is rushed",
            "Load the kicking knee before you swing.",
            "Slow down the approach and create a clear load before contact.",
        ),
        _template(
            "shooting_swing_velocity",
            "UNDER_RANGE",
            "Swing speed is low",
            "Accelerate the kicking foot through the ball.",
            "Build speed gradually after the plant foot is stable.",
        ),
        _template(
            "shooting_contact_extension",
            "UNDER_RANGE",
            "Contact extension is incomplete",
            "Extend through the ball at contact.",
            "Practice striking with a controlled follow-through toward the target.",
        ),
        _template(
            "torso_rotation_stability",
            "UNDER_RANGE",
            "Torso rotation is unstable",
            "Keep your upper body organized through the strike.",
            "Use a slower swing and keep the chest from twisting early.",
        ),
        _template(
            "shooting_balance",
            "UNDER_RANGE",
            "Finish balance needs work",
            "Stay balanced after the strike.",
            "Hold the finish on your support leg before resetting.",
        ),
    ]
)


@dataclass(frozen=True)
class DeterministicFeedbackService:
    def generate(
        self,
        *,
        evaluation_result: DeterministicEvaluationResult,
    ) -> DeterministicFeedbackResult:
        if evaluation_result.status != "COMPLETED":
            return DeterministicFeedbackResult(
                feedback_version=FEEDBACK_VERSION,
                status="FAILED",
                session_id=evaluation_result.session_id,
                overall_feedback_summary=(
                    "Feedback could not be generated because evaluation did not complete."
                ),
                prioritized_feedback_items=[],
                improvement_suggestions=[],
                diagnostic_flags=[
                    "EVALUATION_NOT_COMPLETED",
                    f"EVALUATION_STATUS:{evaluation_result.status}",
                ],
                created_at=datetime.now(UTC),
            )

        ordered_issues = self._order_issues(
            issues=[
                issue
                for issue in evaluation_result.detected_issues
                if self._is_actionable_issue(issue)
            ],
            phase_order={
                phase.phase_id: index
                for index, phase in enumerate(evaluation_result.phase_results)
            },
        )
        diagnostic_flags = list(evaluation_result.diagnostic_flags)
        skipped_not_computable = any(
            issue.computation_status is ComputationStatus.NOT_COMPUTABLE
            for issue in evaluation_result.detected_issues
        )
        if skipped_not_computable:
            diagnostic_flags.append("NOT_COMPUTABLE_ISSUES_SKIPPED")

        feedback_items: list[DeterministicFeedbackItemResponse] = []
        for priority_rank, issue in enumerate(ordered_issues, start=1):
            template, fallback_flag = self._resolve_template(issue)
            if fallback_flag is not None:
                diagnostic_flags.append(fallback_flag)
            feedback_items.append(
                DeterministicFeedbackItemResponse(
                    phase_id=issue.phase_id,
                    metric_id=issue.metric_id,
                    metric_name=issue.metric_name,
                    severity_level=issue.severity_level,
                    affected_body_part=issue.affected_body_part,
                    issue_direction=issue.issue_direction,
                    issue_title=template.issue_title,
                    coaching_cue=template.coaching_cue,
                    improvement_suggestion=template.improvement_suggestion,
                    priority_rank=priority_rank,
                    deviation=issue.deviation,
                )
            )

        if not feedback_items:
            diagnostic_flags.append("NO_ACTIONABLE_ISSUES")

        return DeterministicFeedbackResult(
            feedback_version=FEEDBACK_VERSION,
            status="COMPLETED" if feedback_items else "NO_ACTIONABLE_ISSUES",
            session_id=evaluation_result.session_id,
            overall_feedback_summary=self._build_summary(
                evaluation_result=evaluation_result,
                feedback_items=feedback_items,
            ),
            prioritized_feedback_items=feedback_items,
            improvement_suggestions=self._build_improvement_suggestions(feedback_items),
            diagnostic_flags=self._dedupe(diagnostic_flags),
            created_at=datetime.now(UTC),
        )

    @staticmethod
    def _is_actionable_issue(issue: DeterministicEvaluationIssueResponse) -> bool:
        return (
            issue.computation_status is ComputationStatus.COMPUTED
            and issue.severity_level in {SeverityLevel.MODERATE, SeverityLevel.SEVERE}
        )

    @staticmethod
    def _order_issues(
        *,
        issues: list[DeterministicEvaluationIssueResponse],
        phase_order: dict[str, int],
    ) -> list[DeterministicEvaluationIssueResponse]:
        return [
            issue
            for _, issue in sorted(
                enumerate(issues),
                key=lambda indexed_issue: (
                    -_SEVERITY_PRIORITY[indexed_issue[1].severity_level],
                    -indexed_issue[1].deviation,
                    phase_order.get(indexed_issue[1].phase_id, 999),
                    indexed_issue[0],
                ),
            )
        ]

    @staticmethod
    def _resolve_template(
        issue: DeterministicEvaluationIssueResponse,
    ) -> tuple[FeedbackTemplate, str | None]:
        metric_id = issue.metric_id or issue.metric_name
        lookup_keys: tuple[FeedbackTemplateKey, ...] = (
            (metric_id, issue.issue_direction, issue.severity_level, issue.phase_id),
            (metric_id, issue.issue_direction, issue.severity_level, None),
            (metric_id, issue.issue_direction, None, issue.phase_id),
            (metric_id, issue.issue_direction, None, None),
        )
        for key in lookup_keys:
            template = FEEDBACK_TEMPLATE_REGISTRY.get(key)
            if template is not None:
                return template, None

        readable_metric = _humanize(issue.metric_name)
        readable_phase = _humanize(issue.phase_id)
        readable_body_part = issue.affected_body_part.replace("_", " ")
        if issue.issue_direction == "OVER_RANGE":
            cue = f"Reduce extra movement in your {readable_body_part}."
        elif issue.issue_direction == "UNDER_RANGE":
            cue = f"Add more control through your {readable_body_part}."
        else:
            cue = f"Review your {readable_body_part} control."

        return (
            FeedbackTemplate(
                issue_title=f"Improve {readable_metric}",
                coaching_cue=cue,
                improvement_suggestion=(
                    f"Repeat the {readable_phase} phase slowly and keep the movement controlled."
                ),
            ),
            f"FEEDBACK_TEMPLATE_FALLBACK:{metric_id}",
        )

    @staticmethod
    def _build_summary(
        *,
        evaluation_result: DeterministicEvaluationResult,
        feedback_items: list[DeterministicFeedbackItemResponse],
    ) -> str:
        if feedback_items:
            top_item = feedback_items[0]
            top_focus = top_item.improvement_suggestion
            issue_sentence = (
                f"Main issue: {top_item.issue_title.lower()} in the "
                f"{_humanize(top_item.phase_id)} phase."
            )
        else:
            top_focus = "Keep the same controlled form and build consistency."
            issue_sentence = "No major computed technique issue was detected."

        if evaluation_result.strongest_metrics:
            strongest = evaluation_result.strongest_metrics[0]
            strongest_sentence = (
                f"Strongest area: {_humanize(strongest.metric_name)} during "
                f"{_humanize(strongest.phase_id)}."
            )
        else:
            strongest_sentence = "Strongest area: no scored metric stood out."

        overall_sentence = {
            SeverityLevel.MINOR: "Overall, this session was controlled with minor adjustments needed.",
            SeverityLevel.MODERATE: "Overall, this session showed solid effort with technique details to clean up.",
            SeverityLevel.SEVERE: "Overall, this session needs focused technique work before increasing difficulty.",
        }[evaluation_result.overall_severity]

        return f"{overall_sentence} {strongest_sentence} {issue_sentence} Top focus: {top_focus}"

    @staticmethod
    def _build_improvement_suggestions(
        feedback_items: list[DeterministicFeedbackItemResponse],
    ) -> list[str]:
        suggestions = [item.improvement_suggestion for item in feedback_items]
        return DeterministicFeedbackService._dedupe(suggestions)[:3]

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        deduped: list[str] = []
        for value in values:
            if value not in deduped:
                deduped.append(value)
        return deduped


def _humanize(value: str) -> str:
    return value.replace("_", " ")
