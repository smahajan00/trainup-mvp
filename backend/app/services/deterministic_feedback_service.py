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
            "Your posture changed during the rep",
            "Keep your ribs stacked over your hips before you move.",
            "On the next rep, slow the start and hold the same tall body position.",
        ),
        _template(
            "knee_alignment_score",
            "UNDER_RANGE",
            "Your knees drifted away from your toe line",
            "Keep both knees tracking over the middle toes.",
            "On the next rep, slow the descent and press the knees outward before standing.",
        ),
        _template(
            "torso_alignment",
            "UNDER_RANGE",
            "Your torso position changed too much",
            "Brace first, then keep your chest moving with your hips.",
            "On the next rep, keep the ribs stacked and avoid tipping past your base.",
        ),
        _template(
            "hip_stability",
            "UNDER_RANGE",
            "Your hips shifted during the movement",
            "Keep your hips centered between both feet.",
            "On the next rep, keep even pressure through both legs from start to finish.",
        ),
        _template(
            "repetition_consistency",
            "UNDER_RANGE",
            "Your reps changed shape between attempts",
            "Use the same depth and tempo each rep.",
            "On the next set, slow down and repeat the same target shape three times.",
        ),
        _template(
            "balance_stability",
            "UNDER_RANGE",
            "Your balance drifted during the rep",
            "Stay centered and avoid drifting side to side.",
            "On the next rep, pause briefly in the key position before continuing.",
        ),
        _template(
            "elbow_angle_consistency",
            "UNDER_RANGE",
            "Your elbow path changed between reps",
            "Keep your elbow in the same slot each rep.",
            "On the next rep, rehearse the motion slowly and finish through the same line.",
        ),
        _template(
            "shooting_alignment",
            "UNDER_RANGE",
            "Your shot line drifted off target",
            "Release straight through the target line.",
            "On the next shot, pause at the set point and align the elbow before extending.",
        ),
        _template(
            "shoulder_control",
            "UNDER_RANGE",
            "Your shoulder moved before the rest of the pattern was set",
            "Keep your shoulders quiet through the movement.",
            "On the next rep, start from a stable base and avoid opening the shoulder early.",
        ),
        _template(
            "elbow_extension",
            "UNDER_RANGE",
            "Your press did not finish cleanly",
            "Extend your elbows to a controlled lockout without rushing.",
            "On the next rep, press tall and own the top position before lowering.",
        ),
        _template(
            "wrist_elbow_alignment",
            "UNDER_RANGE",
            "Your wrist and elbow lost their stack",
            "Keep your wrist over your elbow.",
            "On the next rep, use a slower press and keep the hand path vertical.",
        ),
        _template(
            "lockout_control",
            "UNDER_RANGE",
            "Your lockout was not controlled",
            "Finish the rep with control at the top.",
            "On the next rep, pause at lockout and keep the weight from drifting.",
        ),
        _template(
            "shoulder_symmetry",
            "UNDER_RANGE",
            "Your shoulders did not move evenly",
            "Keep both shoulders level and controlled.",
            "On the next set, lower the speed until both sides move together.",
        ),
        _template(
            "stance_width_control",
            "UNDER_RANGE",
            "Your stance width changed during the hold",
            "Keep your feet at a steady athletic width.",
            "On the next rep, reset your base before holding or moving in stance.",
        ),
        _template(
            "knee_flexion",
            "UNDER_RANGE",
            "You came out of your defensive stance too high",
            "Lower your hips slightly more and keep the knees loaded.",
            "On the next rep, hold the loaded position with knees bent over your feet.",
        ),
        _template(
            "hip_level_stability",
            "UNDER_RANGE",
            "Your hip height changed during the stance",
            "Keep your hips low and level.",
            "On the next rep, shorten the hold and rebuild the same hip height.",
        ),
        _template(
            "plant_foot_alignment_ratio",
            "UNDER_RANGE",
            "Your plant foot did not arrive in a consistent spot",
            "Set your support foot beside the ball before the swing.",
            "On the next pass, slow the approach and plant before striking.",
        ),
        _template(
            "instep_backswing_knee_angle",
            "UNDER_RANGE",
            "Your backswing shape rushed the pass",
            "Let the kicking knee fold before the strike.",
            "On the next pass, use a shorter approach and build a smooth backswing.",
        ),
        _template(
            "instep_contact_extension",
            "UNDER_RANGE",
            "Your kicking leg did not extend through contact",
            "Lock the ankle and strike through the center of the ball.",
            "On the next pass, use a slower swing and finish through the target.",
        ),
        _template(
            "instep_torso_tilt",
            "UNDER_RANGE",
            "Your torso leaned away from the pass",
            "Keep your chest over the plant leg.",
            "On the next pass, finish toward the target without falling away.",
        ),
        _template(
            "instep_follow_through_stability",
            "UNDER_RANGE",
            "Your follow-through did not stay on line",
            "Finish with a controlled follow-through.",
            "On the next pass, guide the kicking leg through the target line after contact.",
        ),
        _template(
            "support_foot_distance_ratio",
            "UNDER_RANGE",
            "Your plant foot landed at a different distance",
            "Place your support foot beside the ball.",
            "On the next shot, rehearse the final step so the plant foot lands consistently.",
        ),
        _template(
            "shooting_knee_load",
            "UNDER_RANGE",
            "Your kicking leg loaded too quickly",
            "Load the kicking knee before you swing.",
            "On the next shot, slow the approach and create a clear load before contact.",
        ),
        _template(
            "shooting_swing_velocity",
            "UNDER_RANGE",
            "Your swing did not accelerate through the ball",
            "Accelerate the kicking foot after the plant foot is stable.",
            "On the next shot, build speed gradually after your plant is set.",
        ),
        _template(
            "shooting_contact_extension",
            "UNDER_RANGE",
            "Your shot stopped short at contact",
            "Extend through the ball at contact.",
            "On the next shot, strike with a controlled follow-through toward the target.",
        ),
        _template(
            "torso_rotation_stability",
            "UNDER_RANGE",
            "Your trunk rotated before the shot was controlled",
            "Keep your upper body organized through the strike.",
            "On the next shot, slow the swing and keep the chest from twisting early.",
        ),
        _template(
            "shooting_balance",
            "UNDER_RANGE",
            "Your finish balance broke down",
            "Stay balanced after the strike.",
            "On the next shot, hold the finish on your support leg before resetting.",
        ),
    ]
)


_WHY_IT_MATTERS_BY_METRIC = {
    "posture_accuracy": "Posture gives the rest of the movement a stable base. When it changes, every rep becomes harder to repeat.",
    "knee_alignment_score": "Knee tracking protects the lower body and keeps force moving cleanly through the feet.",
    "torso_alignment": "A steady torso helps your hips and legs do the work instead of losing balance through the upper body.",
    "hip_stability": "Stable hips keep pressure even through both sides so the movement does not drift or twist.",
    "repetition_consistency": "Consistent reps make the pattern trainable and help TrainUp read the same movement target each time.",
    "balance_stability": "Balance lets you finish the skill under control instead of leaking force at the end.",
    "elbow_angle_consistency": "A repeatable elbow path keeps the shot or press on the same line every rep.",
    "shooting_alignment": "Shot alignment keeps the ball moving toward the target instead of drifting off line.",
    "shoulder_control": "Quiet shoulders keep the upper body organized so the release or press stays repeatable.",
    "elbow_extension": "A clean finish gives the rep a clear endpoint and prevents the movement from stopping short.",
    "wrist_elbow_alignment": "Stacking the wrist and elbow keeps force moving vertically instead of drifting forward or sideways.",
    "lockout_control": "A stable lockout shows you own the top position before lowering or resetting.",
    "shoulder_symmetry": "Even shoulder movement keeps one side from compensating for the other.",
    "stance_width_control": "A steady stance width gives you a reliable base for reacting and changing direction.",
    "knee_flexion": "Good knee bend keeps you loaded and ready instead of popping upright.",
    "hip_level_stability": "Level hips keep your defensive base low and balanced.",
    "plant_foot_alignment_ratio": "The plant foot sets the line for the pass before the kicking leg swings.",
    "instep_backswing_knee_angle": "A controlled backswing helps time the strike instead of rushing contact.",
    "instep_contact_extension": "Extending through contact helps the pass travel cleanly through the target line.",
    "instep_torso_tilt": "A stable trunk keeps your body over the ball so the pass does not pull off line.",
    "instep_follow_through_stability": "A controlled follow-through shows the pass finished toward the target.",
    "support_foot_distance_ratio": "Plant-foot distance sets the shooting angle and gives the swing room to finish.",
    "shooting_knee_load": "Loading the kicking knee gives the shot rhythm before acceleration.",
    "shooting_swing_velocity": "Swing speed matters only after the plant foot and body shape are stable.",
    "shooting_contact_extension": "Extending through the ball creates a cleaner strike and follow-through.",
    "torso_rotation_stability": "Controlled trunk rotation keeps power moving through the ball instead of pulling the shot off balance.",
    "shooting_balance": "A balanced finish shows the strike was controlled all the way through.",
}


_SIMPLE_PHRASE_BY_METRIC = {
    "posture_accuracy": "Stay tall and stacked.",
    "knee_alignment_score": "Knees over toes.",
    "torso_alignment": "Brace, then move.",
    "hip_stability": "Keep the hips centered.",
    "repetition_consistency": "Same shape every rep.",
    "balance_stability": "Own the finish.",
    "elbow_angle_consistency": "Same elbow slot.",
    "shooting_alignment": "Release on line.",
    "shoulder_control": "Quiet shoulders.",
    "elbow_extension": "Finish the reach.",
    "wrist_elbow_alignment": "Stack wrist over elbow.",
    "lockout_control": "Control the top.",
    "shoulder_symmetry": "Move both sides together.",
    "stance_width_control": "Hold your base.",
    "knee_flexion": "Stay loaded.",
    "hip_level_stability": "Hips low and level.",
    "plant_foot_alignment_ratio": "Plant beside the ball.",
    "instep_backswing_knee_angle": "Fold, then strike.",
    "instep_contact_extension": "Strike through the ball.",
    "instep_torso_tilt": "Chest over the plant leg.",
    "instep_follow_through_stability": "Finish through target.",
    "support_foot_distance_ratio": "Plant, then swing.",
    "shooting_knee_load": "Load before contact.",
    "shooting_swing_velocity": "Accelerate after the plant.",
    "shooting_contact_extension": "Drive through contact.",
    "torso_rotation_stability": "Keep the trunk organized.",
    "shooting_balance": "Hold the finish.",
}


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
            explanation = self._build_item_explanation(issue=issue, template=template)
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
                    what_happened=explanation["what_happened"],
                    why_it_matters=explanation["why_it_matters"],
                    what_to_fix=explanation["what_to_fix"],
                    next_rep_cue=explanation["next_rep_cue"],
                    simple_coaching_phrase=explanation["simple_coaching_phrase"],
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
    def _build_item_explanation(
        *,
        issue: DeterministicEvaluationIssueResponse,
        template: FeedbackTemplate,
    ) -> dict[str, str]:
        metric_id = issue.metric_id or issue.metric_name
        phase_label = _humanize(issue.phase_id)
        body_part = issue.affected_body_part.replace("_", " ")
        simple_phrase = _SIMPLE_PHRASE_BY_METRIC.get(metric_id, template.coaching_cue)

        return {
            "what_happened": (
                f"{template.issue_title}. It showed up during the {phase_label} phase around your {body_part} control."
            ),
            "why_it_matters": _WHY_IT_MATTERS_BY_METRIC.get(
                metric_id,
                "This pattern matters because it changes how repeatable and controllable the movement feels from rep to rep.",
            ),
            "what_to_fix": template.coaching_cue,
            "next_rep_cue": template.improvement_suggestion,
            "simple_coaching_phrase": simple_phrase,
        }

    @staticmethod
    def _build_summary(
        *,
        evaluation_result: DeterministicEvaluationResult,
        feedback_items: list[DeterministicFeedbackItemResponse],
    ) -> str:
        if feedback_items:
            top_item = feedback_items[0]
            top_focus = top_item.next_rep_cue or top_item.improvement_suggestion
            issue_sentence = (
                f"Start with {top_item.issue_title.lower()} during the "
                f"{_humanize(top_item.phase_id)} phase."
            )
        else:
            top_focus = "Keep the same controlled form and build consistency."
            issue_sentence = "No major computed technique issue was detected."

        if evaluation_result.strongest_metrics:
            strongest = evaluation_result.strongest_metrics[0]
            strongest_sentence = (
                f"Your best pattern was {_humanize(strongest.metric_name)} during "
                f"the {_humanize(strongest.phase_id)} phase."
            )
        else:
            strongest_sentence = "No single scored area stood out as the strongest pattern."

        overall_sentence = {
            SeverityLevel.MINOR: "Overall, this session was controlled with minor adjustments needed.",
            SeverityLevel.MODERATE: "Overall, this session showed solid effort with technique details to clean up.",
            SeverityLevel.SEVERE: "Overall, this session needs focused technique work before increasing difficulty.",
        }[evaluation_result.overall_severity]

        return f"{overall_sentence} {strongest_sentence} {issue_sentence} Next focus: {top_focus}"

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
