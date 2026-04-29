from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Iterable

from app.engines.cognition_engine.phase2a_contract import (
    LEVEL_STRICTNESS_FACTORS,
    PHASE2A_EVALUATION_VERSION,
    PHASE_RANGE_BOUNDARY_MODE,
    DEFENSIVE_STANCE_REQUIRED_LANDMARKS,
    DrillPhase2AContract,
    FOOTBALL_KICK_REQUIRED_LANDMARKS,
    MetricContract,
    SHOULDER_PRESS_REQUIRED_LANDMARKS,
    SQUAT_REQUIRED_LANDMARKS,
    SET_SHOT_REQUIRED_LANDMARKS,
    get_phase2a_contract,
)
from app.models.enums import ComputationStatus, DominantSide, SeverityLevel
from app.models.training_session import TrainingSession
from app.schemas.session import (
    DeterministicEvaluationIssueResponse,
    DeterministicEvaluationResult,
    EvaluationFrameRangeResponse,
    MetricEvaluationResultResponse,
    PhaseEvaluationResultResponse,
    PoseFrameResponse,
    PoseLandmarkCoordinate,
    PoseSequenceResponse,
    RankedMetricResponse,
)

VISIBILITY_THRESHOLD = 0.50


@dataclass(frozen=True)
class PhaseFrameRange:
    phase_id: str
    start_frame_index: int
    end_frame_index: int
    start_timestamp_ms: float
    end_timestamp_ms: float


@dataclass(frozen=True)
class Phase2AEvaluationComputation:
    result: DeterministicEvaluationResult
    metric_results: list[MetricEvaluationResultResponse]


class PhaseSegmentationError(ValueError):
    """Raised when deterministic phase segmentation cannot produce usable ranges."""


class Phase2AEvaluator:
    def evaluate(
        self,
        *,
        session: TrainingSession,
        pose_sequence: PoseSequenceResponse,
        dominant_side: DominantSide | None = None,
        requested_dominant_side: DominantSide | None = None,
        dominant_side_confidence: float | None = None,
        dominant_side_diagnostic_flags: list[str] | None = None,
    ) -> Phase2AEvaluationComputation:
        contract = get_phase2a_contract(session.drill.drill_name)
        effective_dominant_side = (
            session.dominant_side if dominant_side is None else dominant_side
        )
        dominant_side_diagnostic_flags = dominant_side_diagnostic_flags or []
        if contract is None:
            return Phase2AEvaluationComputation(
                result=self._failure_result(
                    session=session,
                    diagnostic_flags=["UNSUPPORTED_DRILL"],
                    requested_dominant_side=requested_dominant_side,
                    resolved_dominant_side=effective_dominant_side,
                    dominant_side_confidence=dominant_side_confidence,
                    dominant_side_diagnostic_flags=dominant_side_diagnostic_flags or None,
                ),
                metric_results=[],
            )

        if session.skill_level not in LEVEL_STRICTNESS_FACTORS:
            return Phase2AEvaluationComputation(
                result=self._failure_result(
                    session=session,
                    diagnostic_flags=["UNSUPPORTED_SKILL_LEVEL"],
                    requested_dominant_side=requested_dominant_side,
                    resolved_dominant_side=effective_dominant_side,
                    dominant_side_confidence=dominant_side_confidence,
                    dominant_side_diagnostic_flags=dominant_side_diagnostic_flags or None,
                ),
                metric_results=[],
            )

        try:
            phase_ranges = self._segment_phases(
                contract=contract,
                frames=pose_sequence.sequence_data,
                dominant_side=effective_dominant_side,
            )
        except PhaseSegmentationError as exc:
            return Phase2AEvaluationComputation(
                result=self._failure_result(
                    session=session,
                    diagnostic_flags=["PHASE_SEGMENTATION_FAILURE", str(exc)],
                    requested_dominant_side=requested_dominant_side,
                    resolved_dominant_side=effective_dominant_side,
                    dominant_side_confidence=dominant_side_confidence,
                    dominant_side_diagnostic_flags=dominant_side_diagnostic_flags or None,
                ),
                metric_results=[],
            )

        metric_results: list[MetricEvaluationResultResponse] = []
        phase_results: list[PhaseEvaluationResultResponse] = []
        detected_issues: list[DeterministicEvaluationIssueResponse] = []

        for phase_range in phase_ranges:
            phase_frames = self._frames_in_range(
                pose_sequence.sequence_data,
                phase_range,
            )
            phase_metric_results = [
                self._compute_metric_result(
                    metric_contract=metric_contract,
                    frames=phase_frames,
                    dominant_side=effective_dominant_side,
                    level_factor=LEVEL_STRICTNESS_FACTORS[session.skill_level],
                )
                for metric_contract in contract.metric_contracts
                if metric_contract.phase_id == phase_range.phase_id
            ]
            metric_results.extend(phase_metric_results)

            phase_issues = [
                self._build_issue(metric_result)
                for metric_result in phase_metric_results
                if self._is_actionable(metric_result)
                or self._is_diagnostic_issue(metric_result)
            ]
            detected_issues.extend(phase_issues)
            phase_results.append(
                PhaseEvaluationResultResponse(
                    phase_id=phase_range.phase_id,
                    frame_range=EvaluationFrameRangeResponse(
                        phase_id=phase_range.phase_id,
                        start_frame_index=phase_range.start_frame_index,
                        end_frame_index=phase_range.end_frame_index,
                        start_timestamp_ms=phase_range.start_timestamp_ms,
                        end_timestamp_ms=phase_range.end_timestamp_ms,
                        boundary_mode=PHASE_RANGE_BOUNDARY_MODE,
                    ),
                    metric_results=phase_metric_results,
                    phase_score=self._aggregate_score(phase_metric_results),
                    phase_severity=self._highest_severity(phase_metric_results),
                    detected_issues=phase_issues,
                )
            )

        overall_score = self._aggregate_phase_score(phase_results)
        result = DeterministicEvaluationResult(
            evaluation_version=PHASE2A_EVALUATION_VERSION,
            status="COMPLETED" if metric_results else "INSUFFICIENT_DATA",
            session_id=session.id,
            sport_id=session.drill.sport_id,
            skill_level=session.skill_level,
            drill_id=session.drill_id,
            phase_results=phase_results,
            overall_score=overall_score,
            overall_severity=self._highest_phase_severity(phase_results),
            detected_issues=detected_issues,
            strongest_metrics=self._rank_metrics(metric_results, strongest=True),
            weakest_metrics=self._rank_metrics(metric_results, strongest=False),
            diagnostic_flags=self._dedupe_strings(
                [
                    *self._build_diagnostic_flags(metric_results),
                    *dominant_side_diagnostic_flags,
                ]
            ),
            requested_dominant_side=requested_dominant_side,
            resolved_dominant_side=effective_dominant_side,
            dominant_side_confidence=dominant_side_confidence,
            dominant_side_diagnostic_flags=(
                dominant_side_diagnostic_flags or None
            ),
        )
        return Phase2AEvaluationComputation(result=result, metric_results=metric_results)

    def _segment_phases(
        self,
        *,
        contract: DrillPhase2AContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> list[PhaseFrameRange]:
        segmenter = SEGMENTATION_REGISTRY.get(contract.drill_id)
        if segmenter is None:
            raise PhaseSegmentationError(
                f"Unsupported segmentation drill_id: {contract.drill_id}."
            )
        return segmenter(
            self,
            frames,
            dominant_side=dominant_side,
            parameters=contract.segmentation_parameters,
        )

    def _segment_bodyweight_squat(
        self,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None = None,
        parameters: dict[str, float] | None = None,
    ) -> list[PhaseFrameRange]:
        parameters = parameters or {}
        candidates = self._usable_frames(frames, SQUAT_REQUIRED_LANDMARKS)
        min_valid_frames = self._segmentation_int(parameters, "min_valid_frames")
        if len(candidates) < min_valid_frames:
            raise PhaseSegmentationError("Missing squat landmarks for phase segmentation.")

        angle_by_index = {
            frame.frame_index: self._average_knee_angle(frame)
            for frame in candidates
        }
        setup_window_frames = self._segmentation_int(parameters, "setup_window_frames")
        first_frames = candidates[: min(setup_window_frames, len(candidates))]
        setup_angle = mean(angle_by_index[frame.frame_index] for frame in first_frames)
        bottom_frame = min(candidates, key=lambda frame: angle_by_index[frame.frame_index])
        bottom_angle = angle_by_index[bottom_frame.frame_index]
        motion_delta = setup_angle - bottom_angle
        min_motion_delta = self._segmentation_parameter(
            parameters,
            "min_knee_motion_delta_deg",
        )
        if motion_delta < min_motion_delta:
            raise PhaseSegmentationError("Knee-angle motion is too small for squat segmentation.")

        setup_threshold = setup_angle - max(
            self._segmentation_parameter(parameters, "boundary_min_delta_deg"),
            motion_delta * self._segmentation_parameter(parameters, "boundary_delta_ratio"),
        )
        pre_bottom = [frame for frame in candidates if frame.frame_index < bottom_frame.frame_index]
        boundary = next(
            (
                frame
                for frame in pre_bottom
                if angle_by_index[frame.frame_index] <= setup_threshold
            ),
            self._segmentation_fallback_frame(
                pre_bottom,
                self._segmentation_parameter(parameters, "fallback_boundary_fraction"),
            ) if pre_bottom else candidates[0],
        )
        start = candidates[0]
        end = candidates[-1]

        return [
            self._range("setup", start, boundary),
            self._range("descent", boundary, bottom_frame),
            self._range("ascent", bottom_frame, end),
        ]

    def _segment_set_shot_form(
        self,
        frames: list[PoseFrameResponse],
        *,
        dominant_side: DominantSide | None,
        parameters: dict[str, float] | None = None,
    ) -> list[PhaseFrameRange]:
        parameters = parameters or {}
        side = self._dominant_prefix(dominant_side)
        candidates = self._usable_frames(frames, SET_SHOT_REQUIRED_LANDMARKS)
        min_valid_frames = self._segmentation_int(parameters, "min_valid_frames")
        if len(candidates) < min_valid_frames:
            raise PhaseSegmentationError("Missing set-shot landmarks for phase segmentation.")

        wrist_name = f"{side}_wrist"
        release_frame = min(candidates, key=lambda frame: frame.landmarks[wrist_name].y)
        pre_release = [
            frame for frame in candidates if frame.frame_index < release_frame.frame_index
        ]
        load_frame = max(
            pre_release,
            key=lambda frame: frame.landmarks[wrist_name].y,
            default=candidates[0],
        )
        start = candidates[0]
        end = candidates[-1]
        setup_boundary = candidates[
            self._phase_boundary_index(
                candidates.index(load_frame),
                self._segmentation_parameter(parameters, "setup_boundary_fraction"),
            )
        ]

        return [
            self._range("setup", start, setup_boundary),
            self._range("load", setup_boundary, load_frame),
            self._range("release", load_frame, release_frame),
            self._range("follow_through", release_frame, end),
        ]

    def _segment_dumbbell_shoulder_press(
        self,
        frames: list[PoseFrameResponse],
        *,
        dominant_side: DominantSide | None = None,
        parameters: dict[str, float] | None = None,
    ) -> list[PhaseFrameRange]:
        parameters = parameters or {}
        candidates = self._usable_frames(frames, SHOULDER_PRESS_REQUIRED_LANDMARKS)
        min_valid_frames = self._segmentation_int(parameters, "min_valid_frames")
        if len(candidates) < min_valid_frames:
            raise PhaseSegmentationError("Missing shoulder-press landmarks for phase segmentation.")

        wrist_y_by_index = {
            frame.frame_index: self._average_wrist_y(frame)
            for frame in candidates
        }
        setup_window_frames = self._segmentation_int(parameters, "setup_window_frames")
        first_frames = candidates[: min(setup_window_frames, len(candidates))]
        setup_wrist_y = mean(wrist_y_by_index[frame.frame_index] for frame in first_frames)
        lockout_frame = min(candidates, key=lambda frame: wrist_y_by_index[frame.frame_index])
        lockout_wrist_y = wrist_y_by_index[lockout_frame.frame_index]
        motion_delta = setup_wrist_y - lockout_wrist_y
        if motion_delta < self._segmentation_parameter(parameters, "min_wrist_motion_delta"):
            raise PhaseSegmentationError("Wrist vertical motion is too small for shoulder-press segmentation.")

        boundary_delta = max(
            self._segmentation_parameter(parameters, "boundary_min_delta"),
            motion_delta * self._segmentation_parameter(parameters, "boundary_delta_ratio"),
        )
        press_threshold = setup_wrist_y - boundary_delta
        return_threshold = lockout_wrist_y + boundary_delta
        pre_lockout = [
            frame for frame in candidates if frame.frame_index < lockout_frame.frame_index
        ]
        post_lockout = [
            frame for frame in candidates if frame.frame_index > lockout_frame.frame_index
        ]
        press_boundary = next(
            (
                frame
                for frame in pre_lockout
                if wrist_y_by_index[frame.frame_index] <= press_threshold
            ),
            self._segmentation_fallback_frame(
                pre_lockout,
                self._segmentation_parameter(parameters, "press_fallback_fraction"),
            ) if pre_lockout else candidates[0],
        )
        return_boundary = next(
            (
                frame
                for frame in post_lockout
                if wrist_y_by_index[frame.frame_index] >= return_threshold
            ),
            self._segmentation_fallback_frame(
                post_lockout,
                self._segmentation_parameter(parameters, "return_fallback_fraction"),
            ) if post_lockout else lockout_frame,
        )

        return [
            self._range("setup", candidates[0], press_boundary),
            self._range("press", press_boundary, lockout_frame),
            self._range("lockout", lockout_frame, return_boundary),
            self._range("return", return_boundary, candidates[-1]),
        ]

    def _segment_defensive_stance(
        self,
        frames: list[PoseFrameResponse],
        *,
        dominant_side: DominantSide | None = None,
        parameters: dict[str, float] | None = None,
    ) -> list[PhaseFrameRange]:
        parameters = parameters or {}
        candidates = self._usable_frames(frames, DEFENSIVE_STANCE_REQUIRED_LANDMARKS)
        min_valid_frames = self._segmentation_int(parameters, "min_valid_frames")
        if len(candidates) < min_valid_frames:
            raise PhaseSegmentationError("Missing defensive-stance landmarks for phase segmentation.")

        knee_angle_by_index = {
            frame.frame_index: self._average_knee_angle(frame)
            for frame in candidates
        }
        setup_window_frames = self._segmentation_int(parameters, "setup_window_frames")
        first_frames = candidates[: min(setup_window_frames, len(candidates))]
        setup_angle = mean(knee_angle_by_index[frame.frame_index] for frame in first_frames)
        low_frame = min(candidates, key=lambda frame: knee_angle_by_index[frame.frame_index])
        low_angle = knee_angle_by_index[low_frame.frame_index]
        motion_delta = setup_angle - low_angle
        min_motion_delta = self._segmentation_parameter(
            parameters,
            "min_knee_motion_delta_deg",
        )
        if motion_delta < min_motion_delta:
            raise PhaseSegmentationError("Knee-angle motion is too small for defensive-stance segmentation.")

        boundary_delta = max(
            self._segmentation_parameter(parameters, "boundary_min_delta_deg"),
            motion_delta * self._segmentation_parameter(parameters, "boundary_delta_ratio"),
        )
        hold_threshold = setup_angle - boundary_delta
        recovery_threshold = low_angle + boundary_delta
        pre_low = [frame for frame in candidates if frame.frame_index < low_frame.frame_index]
        post_low = [frame for frame in candidates if frame.frame_index > low_frame.frame_index]
        hold_boundary = next(
            (
                frame
                for frame in pre_low
                if knee_angle_by_index[frame.frame_index] <= hold_threshold
            ),
            self._segmentation_fallback_frame(
                pre_low,
                self._segmentation_parameter(parameters, "hold_fallback_fraction"),
            ) if pre_low else candidates[0],
        )
        recovery_boundary = next(
            (
                frame
                for frame in post_low
                if knee_angle_by_index[frame.frame_index] >= recovery_threshold
            ),
            self._segmentation_fallback_frame(
                post_low,
                self._segmentation_parameter(parameters, "recovery_fallback_fraction"),
            ) if post_low else low_frame,
        )

        return [
            self._range("setup", candidates[0], hold_boundary),
            self._range("hold", hold_boundary, recovery_boundary),
            self._range("recovery", recovery_boundary, candidates[-1]),
        ]

    def _segment_instep_pass(
        self,
        frames: list[PoseFrameResponse],
        *,
        dominant_side: DominantSide | None = None,
        parameters: dict[str, float] | None = None,
    ) -> list[PhaseFrameRange]:
        parameters = parameters or {}
        side = self._dominant_prefix(dominant_side)
        support_side = self._support_prefix(side)
        candidates = self._usable_frames(frames, FOOTBALL_KICK_REQUIRED_LANDMARKS)
        min_valid_frames = self._segmentation_int(parameters, "min_valid_frames")
        if len(candidates) < min_valid_frames:
            raise PhaseSegmentationError("Missing instep-pass landmarks for phase segmentation.")

        knee_angle_by_index = {
            frame.frame_index: self._kicking_knee_angle(frame, side=side)
            for frame in candidates
        }
        setup_window_frames = self._segmentation_int(parameters, "setup_window_frames")
        first_frames = candidates[: min(setup_window_frames, len(candidates))]
        setup_angle = mean(knee_angle_by_index[frame.frame_index] for frame in first_frames)
        backswing_frame = min(candidates, key=lambda frame: knee_angle_by_index[frame.frame_index])
        backswing_angle = knee_angle_by_index[backswing_frame.frame_index]
        motion_delta = setup_angle - backswing_angle
        min_motion_delta = self._segmentation_parameter(
            parameters,
            "min_kicking_knee_motion_delta_deg",
        )
        if motion_delta < min_motion_delta:
            raise PhaseSegmentationError("Kicking-knee motion is too small for instep-pass segmentation.")

        setup_threshold = setup_angle - max(
            self._segmentation_parameter(parameters, "boundary_min_delta_deg"),
            motion_delta * self._segmentation_parameter(parameters, "boundary_delta_ratio"),
        )
        pre_backswing = [
            frame for frame in candidates if frame.frame_index < backswing_frame.frame_index
        ]
        backswing_boundary = next(
            (
                frame
                for frame in pre_backswing
                if knee_angle_by_index[frame.frame_index] <= setup_threshold
            ),
            self._segmentation_fallback_frame(
                pre_backswing,
                self._segmentation_parameter(parameters, "backswing_fallback_fraction"),
            ) if pre_backswing else candidates[0],
        )
        post_backswing = [
            frame for frame in candidates if frame.frame_index >= backswing_frame.frame_index
        ]
        contact_frame = min(
            post_backswing,
            key=lambda frame: self._point_distance(
                frame,
                f"{side}_ankle",
                f"{support_side}_ankle",
            ),
        )

        return [
            self._range("setup", candidates[0], backswing_boundary),
            self._range("backswing", backswing_boundary, backswing_frame),
            self._range("contact", backswing_frame, contact_frame),
            self._range("follow_through", contact_frame, candidates[-1]),
        ]

    def _segment_basic_shooting_form(
        self,
        frames: list[PoseFrameResponse],
        *,
        dominant_side: DominantSide | None = None,
        parameters: dict[str, float] | None = None,
    ) -> list[PhaseFrameRange]:
        parameters = parameters or {}
        side = self._dominant_prefix(dominant_side)
        support_side = self._support_prefix(side)
        candidates = self._usable_frames(frames, FOOTBALL_KICK_REQUIRED_LANDMARKS)
        min_valid_frames = self._segmentation_int(parameters, "min_valid_frames")
        if len(candidates) < min_valid_frames:
            raise PhaseSegmentationError("Missing shooting-form landmarks for phase segmentation.")

        knee_angle_by_index = {
            frame.frame_index: self._kicking_knee_angle(frame, side=side)
            for frame in candidates
        }
        setup_window_frames = self._segmentation_int(parameters, "setup_window_frames")
        first_frames = candidates[: min(setup_window_frames, len(candidates))]
        setup_angle = mean(knee_angle_by_index[frame.frame_index] for frame in first_frames)
        contact_frame = min(
            candidates,
            key=lambda frame: self._point_distance(
                frame,
                f"{side}_ankle",
                f"{support_side}_ankle",
            ),
        )
        pre_contact = [
            frame for frame in candidates if frame.frame_index < contact_frame.frame_index
        ]
        min_pre_contact_frames = self._segmentation_int(parameters, "min_pre_contact_frames")
        if len(pre_contact) < min_pre_contact_frames:
            raise PhaseSegmentationError("Shooting contact occurs too early for phase segmentation.")

        load_frame = min(pre_contact, key=lambda frame: knee_angle_by_index[frame.frame_index])
        load_angle = knee_angle_by_index[load_frame.frame_index]
        motion_delta = setup_angle - load_angle
        min_motion_delta = self._segmentation_parameter(
            parameters,
            "min_kicking_knee_motion_delta_deg",
        )
        if motion_delta < min_motion_delta:
            raise PhaseSegmentationError("Kicking-knee motion is too small for shooting-form segmentation.")

        load_threshold = setup_angle - max(
            self._segmentation_parameter(parameters, "boundary_min_delta_deg"),
            motion_delta * self._segmentation_parameter(parameters, "boundary_delta_ratio"),
        )
        pre_load = [frame for frame in pre_contact if frame.frame_index < load_frame.frame_index]
        load_boundary = next(
            (
                frame
                for frame in pre_load
                if knee_angle_by_index[frame.frame_index] <= load_threshold
            ),
            self._segmentation_fallback_frame(
                pre_load,
                self._segmentation_parameter(parameters, "load_fallback_fraction"),
            ) if pre_load else candidates[0],
        )

        return [
            self._range("setup", candidates[0], load_boundary),
            self._range("load", load_boundary, load_frame),
            self._range("swing", load_frame, contact_frame),
            self._range("contact", contact_frame, contact_frame),
            self._range("follow_through", contact_frame, candidates[-1]),
        ]

    def _compute_metric_result(
        self,
        *,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
        level_factor: float,
    ) -> MetricEvaluationResultResponse:
        usable_frames = self._usable_frames(frames, metric_contract.required_landmarks)
        if not usable_frames:
            return self._not_computable_metric_result(
                metric_contract=metric_contract,
                diagnostic_flags=["MISSING_REQUIRED_LANDMARKS"],
            )

        calculator = METRIC_CALCULATOR_REGISTRY.get(metric_contract.metric_id)
        if calculator is None:
            return self._not_computable_metric_result(
                metric_contract=metric_contract,
                diagnostic_flags=[
                    "UNSUPPORTED_METRIC_CALCULATOR",
                    f"METRIC_ID:{metric_contract.metric_id}",
                ],
                valid_frame_count=len(usable_frames),
            )

        try:
            raw_value = calculator(self, metric_contract, usable_frames, dominant_side)
        except ValueError as exc:
            return self._not_computable_metric_result(
                metric_contract=metric_contract,
                diagnostic_flags=[
                    "METRIC_PARAMETER_ERROR",
                    str(exc),
                ],
                valid_frame_count=len(usable_frames),
            )
        deviation, issue_direction = self._calculate_deviation(
            raw_value=raw_value,
            metric_contract=metric_contract,
        )
        severity = self._classify_severity(
            deviation=deviation,
            metric_contract=metric_contract,
            level_factor=level_factor,
        )

        return MetricEvaluationResultResponse(
            metric_id=metric_contract.metric_id,
            metric_name=metric_contract.metric_name,
            phase_id=metric_contract.phase_id,
            raw_value=self._round(raw_value),
            unit=metric_contract.unit,
            ideal_min=metric_contract.ideal_min,
            ideal_max=metric_contract.ideal_max,
            deviation=self._round(deviation),
            issue_direction=issue_direction,
            severity_level=severity,
            normalized_score=self._round(self._clamp(raw_value)),
            affected_body_part=metric_contract.affected_body_part,
            computation_status=ComputationStatus.COMPUTED,
            valid_frame_count=len(usable_frames),
            formula_version=metric_contract.formula_version,
            diagnostic_flags=[],
        )

    @staticmethod
    def _not_computable_metric_result(
        *,
        metric_contract: MetricContract,
        diagnostic_flags: list[str],
        valid_frame_count: int = 0,
    ) -> MetricEvaluationResultResponse:
        return MetricEvaluationResultResponse(
            metric_id=metric_contract.metric_id,
            metric_name=metric_contract.metric_name,
            phase_id=metric_contract.phase_id,
            raw_value=None,
            unit=metric_contract.unit,
            ideal_min=metric_contract.ideal_min,
            ideal_max=metric_contract.ideal_max,
            deviation=None,
            issue_direction="NONE",
            severity_level=SeverityLevel.SEVERE,
            normalized_score=None,
            affected_body_part=metric_contract.affected_body_part,
            computation_status=ComputationStatus.NOT_COMPUTABLE,
            valid_frame_count=valid_frame_count,
            formula_version=metric_contract.formula_version,
            diagnostic_flags=diagnostic_flags,
        )

    def _score_posture_accuracy(
        self,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> float:
        target = self._metric_parameter(metric_contract, "target_lean_deg")
        denominator = self._metric_parameter(metric_contract, "denominator")
        return mean(
            self._clamp(1.0 - (abs(self._torso_lean(frame) - target) / denominator))
            for frame in frames
        )

    def _score_knee_alignment(
        self,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> float:
        min_reference = self._metric_parameter(metric_contract, "min_reference")
        offset_denominator = self._metric_parameter(metric_contract, "offset_denominator")
        return mean(
            self._knee_alignment_score(
                frame,
                min_reference=min_reference,
                offset_denominator=offset_denominator,
            )
            for frame in frames
        )

    def _score_torso_alignment(
        self,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> float:
        denominator = self._metric_parameter(metric_contract, "stddev_denominator")
        leans = [self._torso_lean(frame) for frame in frames]
        return self._clamp(1.0 - (pstdev(leans) / denominator if len(leans) > 1 else 0.0))

    def _score_mid_hip_stability(
        self,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> float:
        return self._range_stability_score(
            [self._midpoint(frame, "left_hip", "right_hip").x for frame in frames],
            denominator=self._metric_parameter(metric_contract, "denominator"),
        )

    def _score_repetition_consistency(
        self,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> float:
        denominator = self._metric_parameter(metric_contract, "angle_difference_denominator")
        diffs = [
            abs(self._angle(frame, "left_hip", "left_knee", "left_ankle")
                - self._angle(frame, "right_hip", "right_knee", "right_ankle"))
            for frame in frames
        ]
        return self._clamp(1.0 - (mean(diffs) / denominator))

    def _score_shooting_alignment(
        self,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> float:
        side = self._dominant_prefix(dominant_side)
        shoulder_width_factor = self._metric_parameter(metric_contract, "shoulder_width_factor")
        min_denominator = self._metric_parameter(metric_contract, "min_denominator")
        return mean(
            self._shooting_alignment_score(
                frame,
                side=side,
                shoulder_width_factor=shoulder_width_factor,
                min_denominator=min_denominator,
            )
            for frame in frames
        )

    def _score_elbow_angle(
        self,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> float:
        side = self._dominant_prefix(dominant_side)
        target = self._metric_parameter(metric_contract, "target_angle_deg")
        denominator = self._metric_parameter(metric_contract, "denominator")
        return mean(
            self._clamp(
                1.0
                - (
                    abs(
                        self._angle(
                            frame,
                            f"{side}_shoulder",
                            f"{side}_elbow",
                            f"{side}_wrist",
                        )
                        - target
                    )
                    / denominator
                )
            )
            for frame in frames
        )

    def _score_shoulder_control(
        self,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> float:
        side = self._dominant_prefix(dominant_side)
        denominator = self._metric_parameter(metric_contract, "denominator")
        return mean(
            self._clamp(
                1.0
                - (
                    abs(
                        frame.landmarks[f"{side}_shoulder"].x
                        - frame.landmarks[f"{side}_hip"].x
                    )
                    / denominator
                )
            )
            for frame in frames
        )

    def _score_bilateral_elbow_extension(
        self,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> float:
        target = self._metric_parameter(metric_contract, "target_angle_deg")
        denominator = self._metric_parameter(metric_contract, "denominator")
        return mean(
            self._clamp(1.0 - (abs(self._average_elbow_angle(frame) - target) / denominator))
            for frame in frames
        )

    def _score_wrist_elbow_alignment(
        self,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> float:
        denominator = self._metric_parameter(metric_contract, "denominator")
        return mean(
            self._clamp(
                1.0
                - (
                    mean(
                        [
                            abs(frame.landmarks["left_wrist"].x - frame.landmarks["left_elbow"].x),
                            abs(frame.landmarks["right_wrist"].x - frame.landmarks["right_elbow"].x),
                        ]
                    )
                    / denominator
                )
            )
            for frame in frames
        )

    def _score_lockout_control(
        self,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> float:
        target = self._metric_parameter(metric_contract, "target_angle_deg")
        angle_denominator = self._metric_parameter(metric_contract, "angle_denominator")
        wrist_y_denominator = self._metric_parameter(metric_contract, "wrist_y_denominator")
        elbow_scores = [
            self._clamp(1.0 - (abs(self._average_elbow_angle(frame) - target) / angle_denominator))
            for frame in frames
        ]
        wrist_heights = [self._average_wrist_y(frame) for frame in frames]
        wrist_stability = self._range_stability_score(
            wrist_heights,
            denominator=wrist_y_denominator,
        )
        return mean([mean(elbow_scores), wrist_stability])

    def _score_shoulder_symmetry(
        self,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> float:
        denominator = self._metric_parameter(metric_contract, "denominator")
        return mean(
            self._clamp(
                1.0
                - (
                    abs(frame.landmarks["left_shoulder"].y - frame.landmarks["right_shoulder"].y)
                    + abs(frame.landmarks["left_wrist"].y - frame.landmarks["right_wrist"].y)
                )
                / denominator
            )
            for frame in frames
        )

    def _score_knee_flexion(
        self,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> float:
        target = self._metric_parameter(metric_contract, "target_angle_deg")
        denominator = self._metric_parameter(metric_contract, "denominator")
        return mean(
            self._clamp(1.0 - (abs(self._average_knee_angle(frame) - target) / denominator))
            for frame in frames
        )

    def _score_stance_width_control(
        self,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> float:
        target_ratio = self._metric_parameter(metric_contract, "target_ratio")
        denominator = self._metric_parameter(metric_contract, "denominator")
        min_shoulder_width = self._metric_parameter(metric_contract, "min_shoulder_width")
        return mean(
            self._clamp(
                1.0
                - (
                    abs(
                        (
                            abs(frame.landmarks["right_ankle"].x - frame.landmarks["left_ankle"].x)
                            / max(
                                abs(
                                    frame.landmarks["right_shoulder"].x
                                    - frame.landmarks["left_shoulder"].x
                                ),
                                min_shoulder_width,
                            )
                        )
                        - target_ratio
                    )
                    / denominator
                )
            )
            for frame in frames
        )

    def _score_hip_level_stability(
        self,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> float:
        denominator = self._metric_parameter(metric_contract, "denominator")
        return mean(
            self._clamp(
                1.0
                - (
                    abs(frame.landmarks["left_hip"].y - frame.landmarks["right_hip"].y)
                    / denominator
                )
            )
            for frame in frames
        )

    def _score_support_foot_ratio(
        self,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> float:
        side = self._dominant_prefix(dominant_side)
        support_side = self._support_prefix(side)
        target_ratio = self._metric_parameter(metric_contract, "target_ratio")
        denominator = self._metric_parameter(metric_contract, "denominator")
        min_reference = self._metric_parameter(metric_contract, "min_reference")
        return mean(
            self._clamp(
                1.0
                - (
                    abs(
                        (
                            abs(
                                frame.landmarks[f"{support_side}_ankle"].x
                                - self._midpoint(frame, "left_hip", "right_hip").x
                            )
                            / max(
                                abs(
                                    frame.landmarks["right_shoulder"].x
                                    - frame.landmarks["left_shoulder"].x
                                ),
                                min_reference,
                            )
                        )
                        - target_ratio
                    )
                    / denominator
                )
            )
            for frame in frames
        )

    def _score_kicking_knee_angle(
        self,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> float:
        side = self._dominant_prefix(dominant_side)
        target = self._metric_parameter(metric_contract, "target_angle_deg")
        denominator = self._metric_parameter(metric_contract, "denominator")
        return mean(
            self._clamp(
                1.0
                - (
                    abs(self._kicking_knee_angle(frame, side=side) - target)
                    / denominator
                )
            )
            for frame in frames
        )

    def _score_instep_torso_tilt(
        self,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> float:
        target = self._metric_parameter(metric_contract, "target_tilt_deg")
        denominator = self._metric_parameter(metric_contract, "denominator")
        return mean(
            self._clamp(1.0 - (abs(self._torso_lean(frame) - target) / denominator))
            for frame in frames
        )

    def _score_instep_follow_through_stability(
        self,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> float:
        side = self._dominant_prefix(dominant_side)
        x_denominator = self._metric_parameter(metric_contract, "x_denominator")
        y_denominator = self._metric_parameter(metric_contract, "y_denominator")
        ankle_x = [frame.landmarks[f"{side}_ankle"].x for frame in frames]
        ankle_y = [frame.landmarks[f"{side}_ankle"].y for frame in frames]
        return mean(
            [
                self._range_stability_score(ankle_x, denominator=x_denominator),
                self._range_stability_score(ankle_y, denominator=y_denominator),
            ]
        )

    def _score_shooting_swing_velocity(
        self,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> float:
        side = self._dominant_prefix(dominant_side)
        target_velocity = self._metric_parameter(metric_contract, "target_velocity")
        if target_velocity <= 0:
            raise ValueError("target_velocity must be positive.")
        displacements = self._ankle_displacements(frames, side=side)
        if not displacements:
            raise ValueError("shooting_swing_velocity requires at least two usable frames.")
        return self._clamp(mean(displacements) / target_velocity)

    def _score_torso_rotation_stability(
        self,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> float:
        denominator = self._metric_parameter(metric_contract, "denominator")
        offsets = [
            self._midpoint(frame, "left_shoulder", "right_shoulder").x
            - self._midpoint(frame, "left_hip", "right_hip").x
            for frame in frames
        ]
        return self._clamp(1.0 - (pstdev(offsets) / denominator if len(offsets) > 1 else 0.0))

    def _score_shooting_balance(
        self,
        metric_contract: MetricContract,
        frames: list[PoseFrameResponse],
        dominant_side: DominantSide | None,
    ) -> float:
        side = self._dominant_prefix(dominant_side)
        support_side = self._support_prefix(side)
        hip_x_denominator = self._metric_parameter(metric_contract, "hip_x_denominator")
        support_x_denominator = self._metric_parameter(metric_contract, "support_x_denominator")
        mid_hip_x = [self._midpoint(frame, "left_hip", "right_hip").x for frame in frames]
        support_ankle_x = [frame.landmarks[f"{support_side}_ankle"].x for frame in frames]
        return mean(
            [
                self._range_stability_score(mid_hip_x, denominator=hip_x_denominator),
                self._range_stability_score(
                    support_ankle_x,
                    denominator=support_x_denominator,
                ),
            ]
        )

    @staticmethod
    def _calculate_deviation(
        *,
        raw_value: float,
        metric_contract: MetricContract,
    ) -> tuple[float, str]:
        if metric_contract.range_type == "min_only":
            ideal_min = metric_contract.ideal_min or 0.0
            deviation = max(ideal_min - raw_value, 0.0)
            return deviation, "UNDER_RANGE" if deviation > 0 else "NONE"
        if metric_contract.range_type == "max_only":
            ideal_max = metric_contract.ideal_max or 0.0
            deviation = max(raw_value - ideal_max, 0.0)
            return deviation, "OVER_RANGE" if deviation > 0 else "NONE"

        ideal_min = metric_contract.ideal_min
        ideal_max = metric_contract.ideal_max
        if ideal_min is not None and raw_value < ideal_min:
            return ideal_min - raw_value, "UNDER_RANGE"
        if ideal_max is not None and raw_value > ideal_max:
            return raw_value - ideal_max, "OVER_RANGE"
        return 0.0, "NONE"

    @staticmethod
    def _classify_severity(
        *,
        deviation: float,
        metric_contract: MetricContract,
        level_factor: float,
    ) -> SeverityLevel:
        if deviation <= 0:
            return SeverityLevel.MINOR

        severe_threshold = metric_contract.base_severe_deviation * level_factor
        moderate_threshold = metric_contract.base_moderate_deviation * level_factor
        if deviation >= severe_threshold:
            return SeverityLevel.SEVERE
        if deviation >= moderate_threshold:
            return SeverityLevel.MODERATE
        return SeverityLevel.MINOR

    @staticmethod
    def _is_actionable(metric_result: MetricEvaluationResultResponse) -> bool:
        return (
            metric_result.computation_status == ComputationStatus.COMPUTED
            and metric_result.severity_level in {SeverityLevel.MODERATE, SeverityLevel.SEVERE}
        )

    @staticmethod
    def _build_issue(
        metric_result: MetricEvaluationResultResponse,
    ) -> DeterministicEvaluationIssueResponse:
        return DeterministicEvaluationIssueResponse(
            phase_id=metric_result.phase_id,
            metric_id=metric_result.metric_id,
            metric_name=metric_result.metric_name,
            severity_level=metric_result.severity_level,
            affected_body_part=metric_result.affected_body_part,
            deviation=metric_result.deviation or 0.0,
            issue_direction=metric_result.issue_direction,
            computation_status=metric_result.computation_status,
            diagnostic_flags=metric_result.diagnostic_flags,
        )

    @staticmethod
    def _is_diagnostic_issue(metric_result: MetricEvaluationResultResponse) -> bool:
        return (
            metric_result.computation_status == ComputationStatus.NOT_COMPUTABLE
            and metric_result.severity_level is SeverityLevel.SEVERE
        )

    @staticmethod
    def _usable_frames(
        frames: Iterable[PoseFrameResponse],
        required_landmarks: tuple[str, ...],
    ) -> list[PoseFrameResponse]:
        return [
            frame
            for frame in frames
            if frame.frame_valid
            and all(
                landmark_name in frame.landmarks
                and frame.landmarks[landmark_name].visibility >= VISIBILITY_THRESHOLD
                for landmark_name in required_landmarks
            )
        ]

    @staticmethod
    def _frames_in_range(
        frames: list[PoseFrameResponse],
        phase_range: PhaseFrameRange,
    ) -> list[PoseFrameResponse]:
        return [
            frame
            for frame in frames
            if phase_range.start_frame_index
            <= frame.frame_index
            <= phase_range.end_frame_index
        ]

    @staticmethod
    def _range(
        phase_id: str,
        start_frame: PoseFrameResponse,
        end_frame: PoseFrameResponse,
    ) -> PhaseFrameRange:
        if end_frame.frame_index < start_frame.frame_index:
            end_frame = start_frame
        return PhaseFrameRange(
            phase_id=phase_id,
            start_frame_index=start_frame.frame_index,
            end_frame_index=end_frame.frame_index,
            start_timestamp_ms=start_frame.timestamp_ms,
            end_timestamp_ms=end_frame.timestamp_ms,
        )

    @staticmethod
    def _dominant_prefix(dominant_side: DominantSide | None) -> str:
        return "left" if dominant_side is DominantSide.LEFT else "right"

    @staticmethod
    def _support_prefix(dominant_prefix: str) -> str:
        return "right" if dominant_prefix == "left" else "left"

    @staticmethod
    def _aggregate_score(metric_results: list[MetricEvaluationResultResponse]) -> float:
        scores = [
            metric.normalized_score
            for metric in metric_results
            if metric.computation_status == ComputationStatus.COMPUTED
            and metric.normalized_score is not None
        ]
        return Phase2AEvaluator._round(mean(scores)) if scores else 0.0

    @staticmethod
    def _aggregate_phase_score(phase_results: list[PhaseEvaluationResultResponse]) -> float:
        return (
            Phase2AEvaluator._round(mean(phase.phase_score for phase in phase_results))
            if phase_results
            else 0.0
        )

    @staticmethod
    def _highest_severity(
        metric_results: list[MetricEvaluationResultResponse],
    ) -> SeverityLevel:
        if not metric_results:
            return SeverityLevel.MINOR
        return max(metric_results, key=lambda metric: _SEVERITY_ORDER[metric.severity_level]).severity_level

    @staticmethod
    def _highest_phase_severity(
        phase_results: list[PhaseEvaluationResultResponse],
    ) -> SeverityLevel:
        if not phase_results:
            return SeverityLevel.MINOR
        return max(phase_results, key=lambda phase: _SEVERITY_ORDER[phase.phase_severity]).phase_severity

    @staticmethod
    def _rank_metrics(
        metric_results: list[MetricEvaluationResultResponse],
        *,
        strongest: bool,
    ) -> list[RankedMetricResponse]:
        computed = [
            metric
            for metric in metric_results
            if metric.computation_status == ComputationStatus.COMPUTED
            and metric.normalized_score is not None
        ]
        ranked = sorted(
            computed,
            key=lambda metric: metric.normalized_score or 0.0,
            reverse=strongest,
        )
        return [
            RankedMetricResponse(
                phase_id=metric.phase_id,
                metric_id=metric.metric_id or metric.metric_name,
                metric_name=metric.metric_name,
                score=Phase2AEvaluator._round(metric.normalized_score or 0.0),
            )
            for metric in ranked[:3]
        ]

    @staticmethod
    def _build_diagnostic_flags(
        metric_results: list[MetricEvaluationResultResponse],
    ) -> list[str]:
        flags: list[str] = []
        for metric in metric_results:
            if metric.computation_status == ComputationStatus.NOT_COMPUTABLE:
                metric_id = metric.metric_id or metric.metric_name
                flags.append(f"NOT_COMPUTABLE_METRIC:{metric.phase_id}:{metric_id}")
            flags.extend(metric.diagnostic_flags)
        return list(dict.fromkeys(flags))

    @staticmethod
    def _dedupe_strings(values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))

    @staticmethod
    def _failure_result(
        *,
        session: TrainingSession,
        diagnostic_flags: list[str],
        status: str = "FAILED",
        requested_dominant_side: DominantSide | None = None,
        resolved_dominant_side: DominantSide | None = None,
        dominant_side_confidence: float | None = None,
        dominant_side_diagnostic_flags: list[str] | None = None,
    ) -> DeterministicEvaluationResult:
        return DeterministicEvaluationResult(
            evaluation_version=PHASE2A_EVALUATION_VERSION,
            status=status,
            session_id=session.id,
            sport_id=session.drill.sport_id,
            skill_level=session.skill_level,
            drill_id=session.drill_id,
            phase_results=[],
            overall_score=0.0,
            overall_severity=SeverityLevel.SEVERE,
            detected_issues=[],
            strongest_metrics=[],
            weakest_metrics=[],
            diagnostic_flags=diagnostic_flags,
            requested_dominant_side=requested_dominant_side,
            resolved_dominant_side=resolved_dominant_side,
            dominant_side_confidence=dominant_side_confidence,
            dominant_side_diagnostic_flags=dominant_side_diagnostic_flags,
        )

    @staticmethod
    def _average_knee_angle(frame: PoseFrameResponse) -> float:
        return mean(
            [
                Phase2AEvaluator._angle(frame, "left_hip", "left_knee", "left_ankle"),
                Phase2AEvaluator._angle(frame, "right_hip", "right_knee", "right_ankle"),
            ]
        )

    @staticmethod
    def _average_elbow_angle(frame: PoseFrameResponse) -> float:
        return mean(
            [
                Phase2AEvaluator._angle(
                    frame,
                    "left_shoulder",
                    "left_elbow",
                    "left_wrist",
                ),
                Phase2AEvaluator._angle(
                    frame,
                    "right_shoulder",
                    "right_elbow",
                    "right_wrist",
                ),
            ]
        )

    @staticmethod
    def _average_wrist_y(frame: PoseFrameResponse) -> float:
        return mean(
            [
                frame.landmarks["left_wrist"].y,
                frame.landmarks["right_wrist"].y,
            ]
        )

    @staticmethod
    def _kicking_knee_angle(frame: PoseFrameResponse, *, side: str) -> float:
        return Phase2AEvaluator._angle(
            frame,
            f"{side}_hip",
            f"{side}_knee",
            f"{side}_ankle",
        )

    @staticmethod
    def _point_distance(
        frame: PoseFrameResponse,
        first: str,
        second: str,
    ) -> float:
        first_point = frame.landmarks[first]
        second_point = frame.landmarks[second]
        return math.hypot(first_point.x - second_point.x, first_point.y - second_point.y)

    @staticmethod
    def _ankle_displacements(
        frames: list[PoseFrameResponse],
        *,
        side: str,
    ) -> list[float]:
        displacements: list[float] = []
        for previous, current in zip(frames, frames[1:]):
            previous_ankle = previous.landmarks[f"{side}_ankle"]
            current_ankle = current.landmarks[f"{side}_ankle"]
            displacements.append(
                math.hypot(
                    current_ankle.x - previous_ankle.x,
                    current_ankle.y - previous_ankle.y,
                )
            )
        return displacements

    @staticmethod
    def _knee_alignment_score(
        frame: PoseFrameResponse,
        *,
        min_reference: float,
        offset_denominator: float,
    ) -> float:
        scores = []
        for side in ("left", "right"):
            hip = frame.landmarks[f"{side}_hip"]
            knee = frame.landmarks[f"{side}_knee"]
            ankle = frame.landmarks[f"{side}_ankle"]
            reference = max(abs(hip.x - ankle.x), min_reference)
            offset = abs(knee.x - ankle.x) / reference
            scores.append(Phase2AEvaluator._clamp(1.0 - min(offset / offset_denominator, 1.0)))
        return mean(scores)

    @staticmethod
    def _shooting_alignment_score(
        frame: PoseFrameResponse,
        *,
        side: str,
        shoulder_width_factor: float,
        min_denominator: float,
    ) -> float:
        shoulder = frame.landmarks[f"{side}_shoulder"]
        elbow = frame.landmarks[f"{side}_elbow"]
        wrist = frame.landmarks[f"{side}_wrist"]
        shoulder_width = abs(
            frame.landmarks["left_shoulder"].x - frame.landmarks["right_shoulder"].x
        )
        denominator = max(shoulder_width_factor * shoulder_width, min_denominator)
        deviation = abs(elbow.x - shoulder.x) + abs(wrist.x - elbow.x)
        return Phase2AEvaluator._clamp(1.0 - (deviation / denominator))

    @staticmethod
    def _metric_parameter(metric_contract: MetricContract, name: str) -> float:
        try:
            return metric_contract.parameters[name]
        except KeyError as exc:
            raise ValueError(
                f"Metric {metric_contract.metric_id} is missing parameter {name}."
            ) from exc

    @staticmethod
    def _segmentation_parameter(parameters: dict[str, float], name: str) -> float:
        try:
            return parameters[name]
        except KeyError as exc:
            raise PhaseSegmentationError(
                f"Segmentation config is missing parameter {name}."
            ) from exc

    @classmethod
    def _segmentation_int(cls, parameters: dict[str, float], name: str) -> int:
        value = cls._segmentation_parameter(parameters, name)
        if value < 0:
            raise PhaseSegmentationError(
                f"Segmentation parameter {name} must be non-negative."
            )
        return int(round(value))

    @staticmethod
    def _segmentation_fallback_frame(
        frames: list[PoseFrameResponse],
        fraction: float,
    ) -> PoseFrameResponse:
        if not frames:
            raise PhaseSegmentationError("Segmentation fallback received no frames.")
        index = int(len(frames) * fraction)
        index = min(max(index, 0), len(frames) - 1)
        return frames[index]

    @staticmethod
    def _phase_boundary_index(max_index: int, fraction: float) -> int:
        return min(max(int(max_index * fraction), 0), max_index)

    @staticmethod
    def _torso_lean(frame: PoseFrameResponse) -> float:
        shoulder = Phase2AEvaluator._midpoint(frame, "left_shoulder", "right_shoulder")
        hip = Phase2AEvaluator._midpoint(frame, "left_hip", "right_hip")
        dx = shoulder.x - hip.x
        dy = shoulder.y - hip.y
        return math.degrees(math.atan2(abs(dx), max(abs(dy), 1e-6)))

    @staticmethod
    def _range_stability_score(values: list[float], *, denominator: float) -> float:
        if not values:
            return 0.0
        return Phase2AEvaluator._clamp(1.0 - ((max(values) - min(values)) / denominator))

    @staticmethod
    def _midpoint(
        frame: PoseFrameResponse,
        first: str,
        second: str,
    ) -> PoseLandmarkCoordinate:
        first_point = frame.landmarks[first]
        second_point = frame.landmarks[second]
        return PoseLandmarkCoordinate(
            x=(first_point.x + second_point.x) / 2.0,
            y=(first_point.y + second_point.y) / 2.0,
            visibility=min(first_point.visibility, second_point.visibility),
        )

    @staticmethod
    def _angle(
        frame: PoseFrameResponse,
        first: str,
        vertex: str,
        third: str,
    ) -> float:
        a = frame.landmarks[first]
        b = frame.landmarks[vertex]
        c = frame.landmarks[third]
        ba = (a.x - b.x, a.y - b.y)
        bc = (c.x - b.x, c.y - b.y)
        dot = (ba[0] * bc[0]) + (ba[1] * bc[1])
        norm_ba = math.hypot(*ba)
        norm_bc = math.hypot(*bc)
        if norm_ba <= 1e-9 or norm_bc <= 1e-9:
            return 0.0
        cosine = max(min(dot / (norm_ba * norm_bc), 1.0), -1.0)
        return math.degrees(math.acos(cosine))

    @staticmethod
    def _clamp(value: float) -> float:
        return min(max(value, 0.0), 1.0)

    @staticmethod
    def _round(value: float) -> float:
        return round(float(value), 4)


_SEVERITY_ORDER = {
    SeverityLevel.MINOR: 1,
    SeverityLevel.MODERATE: 2,
    SeverityLevel.SEVERE: 3,
}

SEGMENTATION_REGISTRY = {
    "bodyweight_squat": Phase2AEvaluator._segment_bodyweight_squat,
    "set_shot_form": Phase2AEvaluator._segment_set_shot_form,
    "dumbbell_shoulder_press": Phase2AEvaluator._segment_dumbbell_shoulder_press,
    "defensive_stance": Phase2AEvaluator._segment_defensive_stance,
    "instep_pass": Phase2AEvaluator._segment_instep_pass,
    "basic_shooting_form": Phase2AEvaluator._segment_basic_shooting_form,
}

METRIC_CALCULATOR_REGISTRY = {
    "posture_accuracy": Phase2AEvaluator._score_posture_accuracy,
    "knee_alignment_score": Phase2AEvaluator._score_knee_alignment,
    "torso_alignment": Phase2AEvaluator._score_torso_alignment,
    "hip_stability": Phase2AEvaluator._score_mid_hip_stability,
    "balance_stability": Phase2AEvaluator._score_mid_hip_stability,
    "repetition_consistency": Phase2AEvaluator._score_repetition_consistency,
    "shooting_alignment": Phase2AEvaluator._score_shooting_alignment,
    "elbow_angle_consistency": Phase2AEvaluator._score_elbow_angle,
    "shoulder_control": Phase2AEvaluator._score_shoulder_control,
    "elbow_extension": Phase2AEvaluator._score_bilateral_elbow_extension,
    "wrist_elbow_alignment": Phase2AEvaluator._score_wrist_elbow_alignment,
    "lockout_control": Phase2AEvaluator._score_lockout_control,
    "shoulder_symmetry": Phase2AEvaluator._score_shoulder_symmetry,
    "knee_flexion": Phase2AEvaluator._score_knee_flexion,
    "stance_width_control": Phase2AEvaluator._score_stance_width_control,
    "hip_level_stability": Phase2AEvaluator._score_hip_level_stability,
    "plant_foot_alignment_ratio": Phase2AEvaluator._score_support_foot_ratio,
    "instep_backswing_knee_angle": Phase2AEvaluator._score_kicking_knee_angle,
    "instep_contact_extension": Phase2AEvaluator._score_kicking_knee_angle,
    "instep_torso_tilt": Phase2AEvaluator._score_instep_torso_tilt,
    "instep_follow_through_stability": Phase2AEvaluator._score_instep_follow_through_stability,
    "support_foot_distance_ratio": Phase2AEvaluator._score_support_foot_ratio,
    "shooting_knee_load": Phase2AEvaluator._score_kicking_knee_angle,
    "shooting_swing_velocity": Phase2AEvaluator._score_shooting_swing_velocity,
    "shooting_contact_extension": Phase2AEvaluator._score_kicking_knee_angle,
    "torso_rotation_stability": Phase2AEvaluator._score_torso_rotation_stability,
    "shooting_balance": Phase2AEvaluator._score_shooting_balance,
}
