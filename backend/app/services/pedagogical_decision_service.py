from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterable

from app.models.enums import SeverityLevel, SkillLevel
from app.schemas.session import (
    CorrectionIntensity,
    DeterministicEvaluationResult,
    DeterministicFeedbackItemResponse,
    DeterministicFeedbackResult,
    FuzzyInterpretationResult,
    PedagogicalDecisionResult,
    PedagogicalFocusItemResponse,
    PedagogicalSuppressedItemResponse,
    ToneProfile,
)

_FOCUS_LIMIT_BY_SKILL: dict[SkillLevel, int] = {
    SkillLevel.BEGINNER: 1,
    SkillLevel.INTERMEDIATE: 2,
    SkillLevel.ADVANCED: 3,
}

_TEACHING_STRATEGY_BY_SKILL = {
    SkillLevel.BEGINNER: "single_focus_mastery",
    SkillLevel.INTERMEDIATE: "dual_focus_refinement",
    SkillLevel.ADVANCED: "multi_focus_precision",
}

_TONE_PROFILE_BY_SKILL: dict[SkillLevel, ToneProfile] = {
    SkillLevel.BEGINNER: "supportive_simple",
    SkillLevel.INTERMEDIATE: "corrective_specific",
    SkillLevel.ADVANCED: "technical_performance",
}

_PROGRESSION_ADVICE_BY_SKILL = {
    SkillLevel.BEGINNER: (
        "Repeat the drill with one clear correction and keep the next set simple."
    ),
    SkillLevel.INTERMEDIATE: (
        "Refine the movement on the next set and compare how consistently you can "
        "repeat the target shape."
    ),
    SkillLevel.ADVANCED: (
        "Optimize the same movement under stricter precision and control on the "
        "next repetitions."
    ),
}

_LEARNING_OBJECTIVE_BY_METRIC = {
    "posture_accuracy": "posture",
    "torso_alignment": "posture",
    "instep_torso_tilt": "posture",
    "torso_rotation_stability": "posture",
    "knee_alignment_score": "alignment",
    "shooting_alignment": "alignment",
    "wrist_elbow_alignment": "alignment",
    "plant_foot_alignment_ratio": "alignment",
    "support_foot_distance_ratio": "alignment",
    "knee_flexion": "depth",
    "shooting_knee_load": "depth",
    "lockout_control": "control",
    "repetition_consistency": "control",
    "shooting_swing_velocity": "control",
    "hip_stability": "stability",
    "hip_level_stability": "stability",
    "balance_stability": "balance",
    "shooting_balance": "balance",
    "instep_follow_through_stability": "follow-through",
    "shoulder_control": "control",
    "elbow_extension": "extension",
    "instep_contact_extension": "extension",
    "shooting_contact_extension": "extension",
    "instep_backswing_knee_angle": "control",
    "shoulder_symmetry": "alignment",
    "stance_width_control": "balance",
}

_LEARNING_OBJECTIVE_BY_BODY_PART = {
    "shooting_arm": "follow-through",
    "shooting arm": "follow-through",
    "knees": "alignment",
    "elbow": "extension",
    "shoulders": "stability",
    "shoulder": "stability",
    "hips": "stability",
    "posture": "posture",
    "kicking_leg": "extension",
    "kicking leg": "extension",
    "plant_leg": "balance",
    "plant leg": "balance",
}

_INTENSITY_PRIORITY: dict[CorrectionIntensity, int] = {
    "observe": 0,
    "soft": 1,
    "corrective": 2,
    "direct": 3,
}


@dataclass(frozen=True)
class PedagogicalDecisionService:
    def build_failure_result(
        self,
        *,
        session_id,
        sport_id,
        drill_id,
        skill_level: SkillLevel,
        diagnostic_flags: list[str],
    ) -> PedagogicalDecisionResult:
        return PedagogicalDecisionResult(
            status="FAILED",
            session_id=session_id,
            sport_id=sport_id,
            drill_id=drill_id,
            skill_level=skill_level,
            teaching_strategy=_TEACHING_STRATEGY_BY_SKILL[skill_level],
            selected_focus_items=[],
            suppressed_items=[],
            tone_profile=_TONE_PROFILE_BY_SKILL[skill_level],
            correction_intensity="observe",
            learning_objective="control",
            progression_advice=_PROGRESSION_ADVICE_BY_SKILL[skill_level],
            diagnostic_flags=diagnostic_flags,
            created_at=datetime.now(UTC),
        )

    def decide(
        self,
        *,
        evaluation_result: DeterministicEvaluationResult,
        feedback_result: DeterministicFeedbackResult,
        fuzzy_result: FuzzyInterpretationResult | None = None,
        diagnostic_flags: list[str] | None = None,
    ) -> PedagogicalDecisionResult:
        skill_level = evaluation_result.skill_level
        base_flags = [
            *evaluation_result.diagnostic_flags,
            *feedback_result.diagnostic_flags,
            *(diagnostic_flags or []),
        ]
        fuzzy_index: dict[tuple[str, str], object] = {}

        if fuzzy_result is None:
            base_flags.append("MISSING_FUZZY_INTERPRETATION_RESULT")
        elif fuzzy_result.status in {"COMPLETED", "NO_INTERPRETABLE_METRICS"}:
            fuzzy_index = {
                (
                    metric.phase_id,
                    metric.metric_id or metric.metric_name,
                ): metric
                for metric in fuzzy_result.fuzzy_metric_results
            }
            base_flags.extend(fuzzy_result.diagnostic_flags)
        else:
            base_flags.extend(fuzzy_result.diagnostic_flags)
            base_flags.append("UNUSABLE_FUZZY_INTERPRETATION_RESULT")

        if feedback_result.status == "FAILED":
            return self._failure_result(
                evaluation_result=evaluation_result,
                diagnostic_flags=self._dedupe(
                    [*base_flags, "PEDAGOGICAL_INPUT_FEEDBACK_FAILED"]
                ),
            )

        feedback_items = list(feedback_result.prioritized_feedback_items)
        if not feedback_items:
            return self._no_actionable_result(
                evaluation_result=evaluation_result,
                diagnostic_flags=self._dedupe(
                    [*base_flags, "NO_ACTIONABLE_FEEDBACK_ITEMS"]
                ),
            )

        focus_limit = _FOCUS_LIMIT_BY_SKILL[skill_level]
        tone_profile = _TONE_PROFILE_BY_SKILL[skill_level]
        selected_focus_items: list[PedagogicalFocusItemResponse] = []
        suppressed_items: list[PedagogicalSuppressedItemResponse] = []
        selected_objectives: list[str] = []
        selected_intensities: list[CorrectionIntensity] = []

        for item in feedback_items:
            metric_key = item.metric_id or item.metric_name
            fuzzy_metric = fuzzy_index.get((item.phase_id, metric_key))
            fuzzy_label = (
                getattr(fuzzy_metric, "primary_fuzzy_label", None)
                if getattr(fuzzy_metric, "primary_fuzzy_label", None)
                != "NOT_INTERPRETABLE"
                else None
            )
            dominant_label_confidence = getattr(
                fuzzy_metric,
                "dominant_label_confidence",
                None,
            )
            item_intensity = self._resolve_correction_intensity(
                severity_level=item.severity_level,
                dominant_label_confidence=dominant_label_confidence,
                fuzzy_label=fuzzy_label,
            )

            if len(selected_focus_items) < focus_limit:
                learning_objective = self._resolve_learning_objective(
                    metric_id=item.metric_id or item.metric_name,
                    affected_body_part=item.affected_body_part,
                )
                selected_objectives.append(learning_objective)
                selected_intensities.append(item_intensity)
                selected_focus_items.append(
                    PedagogicalFocusItemResponse(
                        phase_id=item.phase_id,
                        metric_id=item.metric_id,
                        metric_name=item.metric_name,
                        severity_level=item.severity_level,
                        fuzzy_label=fuzzy_label,
                        dominant_label_confidence=dominant_label_confidence,
                        affected_body_part=item.affected_body_part,
                        priority_rank=item.priority_rank,
                        teaching_reason=self._build_teaching_reason(
                            skill_level=skill_level,
                            priority_rank=item.priority_rank,
                            correction_intensity=item_intensity,
                            fuzzy_label=fuzzy_label,
                            dominant_label_confidence=dominant_label_confidence,
                        ),
                        recommended_message_style=(
                            f"{tone_profile}:{item_intensity}"
                        ),
                    )
                )
            else:
                suppressed_items.append(
                    PedagogicalSuppressedItemResponse(
                        phase_id=item.phase_id,
                        metric_id=item.metric_id,
                        metric_name=item.metric_name,
                        severity_level=item.severity_level,
                        priority_rank=item.priority_rank,
                        suppression_reason=(
                            f"Deferred to keep {skill_level.value.lower()} feedback "
                            f"focused on the top {focus_limit} priority area(s)."
                        ),
                    )
                )

        learning_objective = self._select_learning_objective(selected_objectives)
        correction_intensity = self._select_overall_correction_intensity(
            selected_intensities
        )
        return PedagogicalDecisionResult(
            status="COMPLETED",
            session_id=evaluation_result.session_id,
            sport_id=evaluation_result.sport_id,
            drill_id=evaluation_result.drill_id,
            skill_level=skill_level,
            teaching_strategy=_TEACHING_STRATEGY_BY_SKILL[skill_level],
            selected_focus_items=selected_focus_items,
            suppressed_items=suppressed_items,
            tone_profile=tone_profile,
            correction_intensity=correction_intensity,
            learning_objective=learning_objective,
            progression_advice=_PROGRESSION_ADVICE_BY_SKILL[skill_level],
            diagnostic_flags=self._dedupe(base_flags),
            created_at=datetime.now(UTC),
        )

    def _resolve_correction_intensity(
        self,
        *,
        severity_level: SeverityLevel,
        dominant_label_confidence: float | None,
        fuzzy_label: str | None,
    ) -> CorrectionIntensity:
        if severity_level is SeverityLevel.MINOR:
            return "observe"
        if severity_level is SeverityLevel.SEVERE:
            if (
                dominant_label_confidence is not None
                and dominant_label_confidence >= 0.75
            ) or fuzzy_label == "STRONGLY_OFF":
                return "direct"
            return "corrective"
        if dominant_label_confidence is not None and dominant_label_confidence < 0.5:
            return "soft"
        if fuzzy_label in {"STRONGLY_OFF", "MODERATELY_OFF"} and (
            dominant_label_confidence is None
            or dominant_label_confidence >= 0.6
        ):
            return "corrective"
        return "soft"

    @staticmethod
    def _resolve_learning_objective(
        *,
        metric_id: str,
        affected_body_part: str,
    ) -> str:
        if metric_id in _LEARNING_OBJECTIVE_BY_METRIC:
            return _LEARNING_OBJECTIVE_BY_METRIC[metric_id]
        body_part_key = affected_body_part.lower()
        if body_part_key in _LEARNING_OBJECTIVE_BY_BODY_PART:
            return _LEARNING_OBJECTIVE_BY_BODY_PART[body_part_key]
        return "control"

    @staticmethod
    def _build_teaching_reason(
        *,
        skill_level: SkillLevel,
        priority_rank: int,
        correction_intensity: CorrectionIntensity,
        fuzzy_label: str | None,
        dominant_label_confidence: float | None,
    ) -> str:
        parts = [
            (
                f"Priority {priority_rank} item selected for "
                f"{skill_level.value.lower()} coaching emphasis."
            )
        ]
        if fuzzy_label is not None and dominant_label_confidence is not None:
            parts.append(
                f"{fuzzy_label.lower().replace('_', ' ')} deviation with "
                f"{dominant_label_confidence:.2f} confidence supports a "
                f"{correction_intensity} correction."
            )
        else:
            parts.append(
                "Fuzzy confidence was unavailable, so severity and deterministic "
                "priority drive the coaching emphasis."
            )
        return " ".join(parts)

    @staticmethod
    def _select_learning_objective(selected_objectives: list[str]) -> str:
        if not selected_objectives:
            return "control"
        counts: dict[str, int] = {}
        for objective in selected_objectives:
            counts[objective] = counts.get(objective, 0) + 1
        return sorted(
            counts,
            key=lambda objective: (-counts[objective], selected_objectives.index(objective)),
        )[0]

    @staticmethod
    def _select_overall_correction_intensity(
        intensities: Iterable[CorrectionIntensity],
    ) -> CorrectionIntensity:
        selected = list(intensities)
        if not selected:
            return "observe"
        return max(selected, key=lambda value: _INTENSITY_PRIORITY[value])

    @staticmethod
    def _failure_result(
        *,
        evaluation_result: DeterministicEvaluationResult,
        diagnostic_flags: list[str],
    ) -> PedagogicalDecisionResult:
        skill_level = evaluation_result.skill_level
        return PedagogicalDecisionResult(
            status="FAILED",
            session_id=evaluation_result.session_id,
            sport_id=evaluation_result.sport_id,
            drill_id=evaluation_result.drill_id,
            skill_level=skill_level,
            teaching_strategy=_TEACHING_STRATEGY_BY_SKILL[skill_level],
            selected_focus_items=[],
            suppressed_items=[],
            tone_profile=_TONE_PROFILE_BY_SKILL[skill_level],
            correction_intensity="observe",
            learning_objective="control",
            progression_advice=_PROGRESSION_ADVICE_BY_SKILL[skill_level],
            diagnostic_flags=diagnostic_flags,
            created_at=datetime.now(UTC),
        )

    @staticmethod
    def _no_actionable_result(
        *,
        evaluation_result: DeterministicEvaluationResult,
        diagnostic_flags: list[str],
    ) -> PedagogicalDecisionResult:
        skill_level = evaluation_result.skill_level
        return PedagogicalDecisionResult(
            status="NO_ACTIONABLE_FEEDBACK",
            session_id=evaluation_result.session_id,
            sport_id=evaluation_result.sport_id,
            drill_id=evaluation_result.drill_id,
            skill_level=skill_level,
            teaching_strategy=_TEACHING_STRATEGY_BY_SKILL[skill_level],
            selected_focus_items=[],
            suppressed_items=[],
            tone_profile=_TONE_PROFILE_BY_SKILL[skill_level],
            correction_intensity="observe",
            learning_objective="control",
            progression_advice=_PROGRESSION_ADVICE_BY_SKILL[skill_level],
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
