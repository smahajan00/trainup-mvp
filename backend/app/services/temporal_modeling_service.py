from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from math import dist
from statistics import mean
from uuid import UUID

from app.engines.temporal_engine.temporal_contract import (
    TEMPORAL_MODEL_VERSION,
    TemporalThresholdConfig,
    get_temporal_threshold_config,
)
from app.models.enums import SkillLevel
from app.schemas.session import (
    DeterministicEvaluationResult,
    EvaluationFrameRangeResponse,
    FuzzyInterpretationResult,
    PhaseEvaluationResultResponse,
    PoseFrameResponse,
    PoseSequenceResponse,
    TemporalModelingResult,
    TemporalPhaseResultResponse,
    TemporalTransitionResultResponse,
)

_BODY_PART_REGION_HINTS = {
    "lower_body": ("knee", "hip", "ankle", "foot", "leg"),
    "upper_body": ("shoulder", "elbow", "wrist", "arm", "hand"),
    "core": ("torso", "trunk", "core", "spine", "chest", "posture"),
}

_STATE_PRIORITY = {
    "INCOMPLETE": 5,
    "UNCERTAIN": 4,
    "JERKY": 3,
    "RUSHED": 2,
    "CONTROLLED": 1,
    "STABLE": 0,
}


def compute_valid_frame_ratio(frames: list[PoseFrameResponse]) -> float:
    if not frames:
        return 0.0
    return round(sum(frame.frame_valid for frame in frames) / len(frames), 4)


def compute_velocity_sequence(
    *,
    frames: list[PoseFrameResponse],
    keypoints: tuple[str, ...],
    config: TemporalThresholdConfig,
) -> list[float]:
    velocities: list[float] = []
    for previous, current in zip(frames, frames[1:], strict=False):
        if not previous.frame_valid or not current.frame_valid:
            continue
        delta_ms = current.timestamp_ms - previous.timestamp_ms
        if delta_ms <= 0:
            continue
        displacements: list[float] = []
        for keypoint in keypoints:
            previous_landmark = previous.landmarks.get(keypoint)
            current_landmark = current.landmarks.get(keypoint)
            if previous_landmark is None or current_landmark is None:
                continue
            displacements.append(
                dist(
                    (previous_landmark.x, previous_landmark.y),
                    (current_landmark.x, current_landmark.y),
                )
            )
        if not displacements:
            continue
        raw_velocity = mean(displacements) / delta_ms * 1000.0
        velocities.append(round(min(1.0, raw_velocity / config.velocity_normalizer), 4))
    return velocities


def compute_average_velocity_proxy(velocity_sequence: list[float]) -> float:
    if not velocity_sequence:
        return 0.0
    return round(mean(velocity_sequence), 4)


def compute_acceleration_change_proxy(velocity_sequence: list[float]) -> float:
    if len(velocity_sequence) < 2:
        return 0.0
    acceleration_changes = [
        abs(current - previous)
        for previous, current in zip(velocity_sequence, velocity_sequence[1:], strict=False)
    ]
    return round(mean(acceleration_changes), 4)


def compute_smoothness_proxy(acceleration_change_proxy: float) -> float:
    return round(max(0.0, 1.0 - acceleration_change_proxy), 4)


def assign_temporal_state(
    *,
    frame_count: int,
    phase_duration_ms: float,
    valid_frame_ratio: float,
    average_velocity_proxy: float,
    smoothness_proxy: float,
    acceleration_change_proxy: float,
    fuzzy_confidence: float | None,
    diagnostic_flags: list[str],
    config: TemporalThresholdConfig,
) -> tuple[str, float]:
    if (
        frame_count < config.minimum_phase_frames
        or phase_duration_ms < config.minimum_phase_duration_ms
        or valid_frame_ratio < config.incomplete_valid_frame_ratio
    ):
        confidence = max(
            1.0 - valid_frame_ratio,
            1.0 - min(frame_count / config.minimum_phase_frames, 1.0),
        )
        return "INCOMPLETE", round(min(1.0, confidence), 4)

    if (
        fuzzy_confidence is not None
        and fuzzy_confidence < config.uncertain_fuzzy_confidence_max
    ) or (
        valid_frame_ratio < config.uncertain_valid_frame_ratio and diagnostic_flags
    ):
        confidence = max(
            1.0 - (fuzzy_confidence if fuzzy_confidence is not None else 0.5),
            1.0 - valid_frame_ratio,
        )
        return "UNCERTAIN", round(min(1.0, confidence), 4)

    if (
        smoothness_proxy <= config.jerky_smoothness_max
        or acceleration_change_proxy >= config.jerky_acceleration_min
    ):
        confidence = max(acceleration_change_proxy, 1.0 - smoothness_proxy)
        return "JERKY", round(min(1.0, confidence), 4)

    if (
        phase_duration_ms <= config.rushed_duration_ms
        and average_velocity_proxy >= config.rushed_velocity_min
    ):
        rushed_by_speed = max(
            0.0,
            (average_velocity_proxy - config.rushed_velocity_min)
            / max(1.0 - config.rushed_velocity_min, 1e-6),
        )
        rushed_by_duration = max(
            0.0,
            1.0 - (phase_duration_ms / max(config.rushed_duration_ms, 1.0)),
        )
        return "RUSHED", round(min(1.0, max(rushed_by_speed, rushed_by_duration)), 4)

    if (
        valid_frame_ratio >= config.stable_valid_frame_ratio
        and average_velocity_proxy <= config.stable_velocity_max
        and smoothness_proxy >= config.stable_smoothness_min
    ):
        stability_components = [
            valid_frame_ratio,
            smoothness_proxy,
            max(
                0.0,
                1.0 - (average_velocity_proxy / max(config.stable_velocity_max, 1e-6)),
            ),
        ]
        return "STABLE", round(min(1.0, mean(stability_components)), 4)

    controlled_confidence = mean([valid_frame_ratio, smoothness_proxy])
    return "CONTROLLED", round(min(1.0, controlled_confidence), 4)


@dataclass(frozen=True)
class TemporalModelingService:
    config: TemporalThresholdConfig = get_temporal_threshold_config()

    def build_failure_result(
        self,
        *,
        session_id: UUID,
        sport_id: UUID,
        drill_id: UUID,
        skill_level: SkillLevel,
        diagnostic_flags: list[str],
        status: str = "FAILED",
    ) -> TemporalModelingResult:
        return TemporalModelingResult(
            temporal_model_version=TEMPORAL_MODEL_VERSION,
            status=status,
            session_id=session_id,
            sport_id=sport_id,
            drill_id=drill_id,
            skill_level=skill_level,
            phase_temporal_results=[],
            transition_results=[],
            overall_temporal_state="UNCERTAIN",
            temporal_summary="Temporal movement analysis could not be generated.",
            diagnostic_flags=self._dedupe(diagnostic_flags),
            created_at=datetime.now(UTC),
        )

    def model(
        self,
        *,
        pose_sequence: PoseSequenceResponse,
        evaluation_result: DeterministicEvaluationResult,
        fuzzy_result: FuzzyInterpretationResult | None = None,
    ) -> TemporalModelingResult:
        diagnostic_flags = [
            *pose_sequence.diagnostic_flags,
            *evaluation_result.diagnostic_flags,
        ]

        phase_fuzzy_confidence: dict[str, float] = {}
        if fuzzy_result is None:
            diagnostic_flags.append("MISSING_FUZZY_INTERPRETATION_RESULT")
        elif fuzzy_result.status in {"COMPLETED", "NO_INTERPRETABLE_METRICS"}:
            diagnostic_flags.extend(fuzzy_result.diagnostic_flags)
            phase_fuzzy_confidence = self._build_phase_fuzzy_confidence(fuzzy_result)
        else:
            diagnostic_flags.extend(fuzzy_result.diagnostic_flags)
            diagnostic_flags.append(
                f"UNUSABLE_FUZZY_INTERPRETATION_RESULT:{fuzzy_result.status}"
            )

        if not evaluation_result.phase_results:
            return TemporalModelingResult(
                temporal_model_version=TEMPORAL_MODEL_VERSION,
                status="INSUFFICIENT_DATA",
                session_id=evaluation_result.session_id,
                sport_id=evaluation_result.sport_id,
                drill_id=evaluation_result.drill_id,
                skill_level=evaluation_result.skill_level,
                phase_temporal_results=[],
                transition_results=[],
                overall_temporal_state="INCOMPLETE",
                temporal_summary="No phase ranges were available for temporal movement analysis.",
                diagnostic_flags=self._dedupe([*diagnostic_flags, "MISSING_PHASE_RANGES"]),
                created_at=datetime.now(UTC),
            )

        phase_temporal_results = [
            self._model_phase(
                pose_sequence=pose_sequence,
                phase=phase,
                fuzzy_confidence=phase_fuzzy_confidence.get(phase.phase_id),
            )
            for phase in evaluation_result.phase_results
        ]
        transition_results = self._build_transition_results(evaluation_result.phase_results)

        if all(result.temporal_state == "INCOMPLETE" for result in phase_temporal_results):
            diagnostic_flags.append("INSUFFICIENT_VALID_PHASE_DATA")
            status = "INSUFFICIENT_DATA"
        else:
            status = "COMPLETED"

        if any(not transition.transition_valid for transition in transition_results):
            diagnostic_flags.append("TEMPORAL_TRANSITION_INCONSISTENT")

        highest_state_phase = max(
            phase_temporal_results,
            key=lambda phase: (
                _STATE_PRIORITY[phase.temporal_state],
                phase.state_confidence,
                phase.phase_id,
            ),
        )
        overall_temporal_state = self._resolve_overall_state(
            phase_temporal_results=phase_temporal_results,
            transition_results=transition_results,
        )
        return TemporalModelingResult(
            temporal_model_version=TEMPORAL_MODEL_VERSION,
            status=status,
            session_id=evaluation_result.session_id,
            sport_id=evaluation_result.sport_id,
            drill_id=evaluation_result.drill_id,
            skill_level=evaluation_result.skill_level,
            phase_temporal_results=phase_temporal_results,
            transition_results=transition_results,
            overall_temporal_state=overall_temporal_state,
            temporal_summary=self._build_summary(
                overall_temporal_state=overall_temporal_state,
                phase_temporal_results=phase_temporal_results,
                transition_results=transition_results,
                highest_state_phase=highest_state_phase,
            ),
            diagnostic_flags=self._dedupe(
                [
                    *diagnostic_flags,
                    *[
                        flag
                        for result in phase_temporal_results
                        for flag in result.diagnostic_flags
                    ],
                    *[
                        flag
                        for transition in transition_results
                        for flag in transition.diagnostic_flags
                    ],
                ]
            ),
            created_at=datetime.now(UTC),
        )

    def _model_phase(
        self,
        *,
        pose_sequence: PoseSequenceResponse,
        phase: PhaseEvaluationResultResponse,
        fuzzy_confidence: float | None,
    ) -> TemporalPhaseResultResponse:
        phase_frames = self._phase_frames(
            pose_sequence=pose_sequence,
            frame_range=phase.frame_range,
        )
        frame_count = len(phase_frames)
        phase_duration_ms = round(
            max(
                0.0,
                phase.frame_range.end_timestamp_ms - phase.frame_range.start_timestamp_ms,
            ),
            4,
        )
        valid_frame_ratio = compute_valid_frame_ratio(phase_frames)
        diagnostic_flags: list[str] = []

        if frame_count == 0:
            diagnostic_flags.append("MISSING_PHASE_FRAMES")
        if phase_duration_ms == 0.0:
            diagnostic_flags.append("ZERO_DURATION_PHASE")

        keypoints = self._resolve_phase_keypoints(phase)
        velocity_sequence = compute_velocity_sequence(
            frames=phase_frames,
            keypoints=keypoints,
            config=self.config,
        )
        if frame_count > 1 and not velocity_sequence:
            diagnostic_flags.append("MISSING_TEMPORAL_KEYPOINTS")

        average_velocity_proxy = compute_average_velocity_proxy(velocity_sequence)
        acceleration_change_proxy = compute_acceleration_change_proxy(velocity_sequence)
        smoothness_proxy = compute_smoothness_proxy(acceleration_change_proxy)
        temporal_state, state_confidence = assign_temporal_state(
            frame_count=frame_count,
            phase_duration_ms=phase_duration_ms,
            valid_frame_ratio=valid_frame_ratio,
            average_velocity_proxy=average_velocity_proxy,
            smoothness_proxy=smoothness_proxy,
            acceleration_change_proxy=acceleration_change_proxy,
            fuzzy_confidence=fuzzy_confidence,
            diagnostic_flags=diagnostic_flags,
            config=self.config,
        )
        return TemporalPhaseResultResponse(
            phase_id=phase.phase_id,
            frame_count=frame_count,
            phase_duration_ms=phase_duration_ms,
            valid_frame_ratio=valid_frame_ratio,
            average_velocity_proxy=average_velocity_proxy,
            smoothness_proxy=smoothness_proxy,
            acceleration_change_proxy=acceleration_change_proxy,
            temporal_state=temporal_state,
            state_confidence=state_confidence,
            diagnostic_flags=diagnostic_flags,
        )

    def _build_transition_results(
        self,
        phase_results: list[PhaseEvaluationResultResponse],
    ) -> list[TemporalTransitionResultResponse]:
        transitions: list[TemporalTransitionResultResponse] = []
        for previous_phase, current_phase in zip(
            phase_results,
            phase_results[1:],
            strict=False,
        ):
            gap_ms = round(
                current_phase.frame_range.start_timestamp_ms
                - previous_phase.frame_range.end_timestamp_ms,
                4,
            )
            phase_order_valid = (
                current_phase.frame_range.start_frame_index
                >= previous_phase.frame_range.start_frame_index
                and current_phase.frame_range.end_frame_index
                >= previous_phase.frame_range.end_frame_index
            )
            diagnostic_flags: list[str] = []
            if gap_ms < 0:
                diagnostic_flags.append("NEGATIVE_TRANSITION_GAP")
            if gap_ms > self.config.transition_gap_tolerance_ms:
                diagnostic_flags.append("TRANSITION_GAP_TOO_LARGE")
            if not phase_order_valid:
                diagnostic_flags.append("PHASE_ORDER_INVALID")

            transitions.append(
                TemporalTransitionResultResponse(
                    from_phase=previous_phase.phase_id,
                    to_phase=current_phase.phase_id,
                    transition_valid=(
                        phase_order_valid
                        and 0.0 <= gap_ms <= self.config.transition_gap_tolerance_ms
                    ),
                    transition_gap_ms=gap_ms,
                    phase_order_valid=phase_order_valid,
                    diagnostic_flags=diagnostic_flags,
                )
            )
        return transitions

    def _resolve_overall_state(
        self,
        *,
        phase_temporal_results: list[TemporalPhaseResultResponse],
        transition_results: list[TemporalTransitionResultResponse],
    ) -> str:
        states = [result.temporal_state for result in phase_temporal_results]
        if not states:
            return "INCOMPLETE"
        if all(state == "INCOMPLETE" for state in states):
            return "INCOMPLETE"
        if "UNCERTAIN" in states:
            return "UNCERTAIN"
        if "JERKY" in states:
            return "JERKY"
        if "RUSHED" in states:
            return "RUSHED"
        if all(state == "STABLE" for state in states) and all(
            transition.transition_valid for transition in transition_results
        ):
            return "STABLE"
        return "CONTROLLED"

    def _build_summary(
        self,
        *,
        overall_temporal_state: str,
        phase_temporal_results: list[TemporalPhaseResultResponse],
        transition_results: list[TemporalTransitionResultResponse],
        highest_state_phase: TemporalPhaseResultResponse,
    ) -> str:
        invalid_transition_count = sum(
            not transition.transition_valid for transition in transition_results
        )
        if overall_temporal_state == "INCOMPLETE":
            return "Temporal movement analysis is limited because phase coverage is incomplete."
        if overall_temporal_state == "UNCERTAIN":
            return (
                "Temporal movement analysis is uncertain, with the greatest instability in "
                f"the {highest_state_phase.phase_id} phase."
            )
        if overall_temporal_state == "JERKY":
            return (
                "Temporal movement analysis indicates jerky motion, especially during the "
                f"{highest_state_phase.phase_id} phase."
            )
        if overall_temporal_state == "RUSHED":
            return (
                "Temporal movement analysis indicates rushed execution in the "
                f"{highest_state_phase.phase_id} phase."
            )
        if overall_temporal_state == "STABLE":
            return "Temporal movement analysis indicates stable phase timing and consistent transitions."
        if invalid_transition_count > 0:
            return (
                "Temporal movement analysis is broadly controlled, but some phase transitions "
                "need cleaner continuity."
            )
        return "Temporal movement analysis indicates controlled pacing and mostly consistent phase transitions."

    def _build_phase_fuzzy_confidence(
        self,
        fuzzy_result: FuzzyInterpretationResult,
    ) -> dict[str, float]:
        phase_confidences: dict[str, list[float]] = {}
        for metric in fuzzy_result.fuzzy_metric_results:
            if metric.dominant_label_confidence is None:
                continue
            phase_confidences.setdefault(metric.phase_id, []).append(
                metric.dominant_label_confidence
            )
        return {
            phase_id: round(mean(confidences), 4)
            for phase_id, confidences in phase_confidences.items()
        }

    def _phase_frames(
        self,
        *,
        pose_sequence: PoseSequenceResponse,
        frame_range: EvaluationFrameRangeResponse,
    ) -> list[PoseFrameResponse]:
        return [
            frame
            for frame in pose_sequence.sequence_data
            if frame_range.start_frame_index <= frame.frame_index <= frame_range.end_frame_index
        ]

    def _resolve_phase_keypoints(
        self,
        phase: PhaseEvaluationResultResponse,
    ) -> tuple[str, ...]:
        selected_regions: set[str] = set()
        for metric in phase.metric_results:
            affected = metric.affected_body_part.lower()
            for region, hints in _BODY_PART_REGION_HINTS.items():
                if any(hint in affected for hint in hints):
                    selected_regions.add(region)

        keypoints: list[str] = []
        for region in sorted(selected_regions):
            keypoints.extend(self.config.body_region_keypoints.get(region, ()))
        return tuple(dict.fromkeys(keypoints)) or self.config.default_keypoints

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        deduped: list[str] = []
        for value in values:
            if value not in deduped:
                deduped.append(value)
        return deduped
