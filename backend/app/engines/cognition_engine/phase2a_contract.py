from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.models.enums import SkillLevel
from app.utils.phase0_contract import (
    PHASE0_FORMULA_VERSION,
    resolve_affected_body_part,
)

RangeType = Literal["closed_range", "min_only", "max_only"]
PHASE2A_EVALUATION_VERSION = "phase2c_v0_1_0"
PHASE_RANGE_BOUNDARY_MODE = "inclusive_overlapping"


@dataclass(frozen=True)
class MetricContract:
    metric_id: str
    metric_name: str
    phase_id: str
    description: str
    required_landmarks: tuple[str, ...]
    computation: str
    parameters: dict[str, float]
    range_type: RangeType
    ideal_min: float | None
    ideal_max: float | None
    unit: str
    base_moderate_deviation: float
    base_severe_deviation: float
    affected_body_part: str
    formula_version: str = PHASE0_FORMULA_VERSION


@dataclass(frozen=True)
class DrillPhase2AContract:
    drill_id: str
    drill_name: str
    phases: tuple[str, ...]
    segmentation_formula: str
    segmentation_parameters: dict[str, float]
    requires_dominant_side: bool
    metric_contracts: tuple[MetricContract, ...]


LEVEL_STRICTNESS_FACTORS: dict[SkillLevel, float] = {
    SkillLevel.BEGINNER: 1.25,
    SkillLevel.INTERMEDIATE: 1.00,
    SkillLevel.ADVANCED: 0.75,
}


SQUAT_REQUIRED_LANDMARKS = (
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
)

SET_SHOT_REQUIRED_LANDMARKS = (
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
)

SHOULDER_PRESS_REQUIRED_LANDMARKS = (
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
)

DEFENSIVE_STANCE_REQUIRED_LANDMARKS = (
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
)

FOOTBALL_KICK_REQUIRED_LANDMARKS = (
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
)


def _score_metric(
    *,
    metric_id: str,
    metric_name: str,
    phase_id: str,
    description: str,
    required_landmarks: tuple[str, ...],
    computation: str,
    parameters: dict[str, float],
    ideal_min: float,
    base_moderate_deviation: float,
    base_severe_deviation: float,
) -> MetricContract:
    return MetricContract(
        metric_id=metric_id,
        metric_name=metric_name,
        phase_id=phase_id,
        description=description,
        required_landmarks=required_landmarks,
        computation=computation,
        parameters=parameters,
        range_type="closed_range",
        ideal_min=ideal_min,
        ideal_max=1.0,
        unit="score",
        base_moderate_deviation=base_moderate_deviation,
        base_severe_deviation=base_severe_deviation,
        affected_body_part=resolve_affected_body_part(metric_name),
    )


BODYWEIGHT_SQUAT_CONTRACT = DrillPhase2AContract(
    drill_id="bodyweight_squat",
    drill_name="Bodyweight Squat",
    phases=("setup", "descent", "ascent"),
    segmentation_formula=(
        "Compute bilateral knee angle angle(hip,knee,ankle) for valid frames. "
        "Use first valid frame as motion start, minimum average knee angle as bottom, "
        "and the first pre-bottom frame whose knee angle drops materially from setup "
        "as setup/descent boundary."
    ),
    segmentation_parameters={
        "min_valid_frames": 3.0,
        "setup_window_frames": 5.0,
        "min_knee_motion_delta_deg": 3.0,
        "boundary_min_delta_deg": 5.0,
        "boundary_delta_ratio": 0.25,
        "fallback_boundary_fraction": 0.25,
    },
    requires_dominant_side=False,
    metric_contracts=(
        _score_metric(
            metric_id="posture_accuracy",
            metric_name="posture_accuracy",
            phase_id="setup",
            description="Torso posture score from shoulder-midpoint to hip-midpoint lean.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_hip",
                "right_hip",
            ),
            computation=(
                "score = mean(clamp(1 - abs(torso_lean_deg - 12) / 30, 0, 1)); "
                "torso_lean_deg = atan2(abs(dx_mid_shoulder_hip), abs(dy_mid_shoulder_hip))."
            ),
            parameters={"target_lean_deg": 12.0, "denominator": 30.0},
            ideal_min=0.82,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
        _score_metric(
            metric_id="knee_alignment_score",
            metric_name="knee_alignment_score",
            phase_id="descent",
            description="Knee-over-ankle alignment score during descent.",
            required_landmarks=(
                "left_hip",
                "right_hip",
                "left_knee",
                "right_knee",
                "left_ankle",
                "right_ankle",
            ),
            computation=(
                "score = mean(1 - min(abs(knee.x - ankle.x) / max(abs(hip.x - ankle.x), 0.05) / 2, 1)) "
                "computed bilaterally over valid phase frames."
            ),
            parameters={"min_reference": 0.05, "offset_denominator": 2.0},
            ideal_min=0.78,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
        _score_metric(
            metric_id="torso_alignment",
            metric_name="torso_alignment",
            phase_id="descent",
            description="Torso lean consistency score through descent.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_hip",
                "right_hip",
            ),
            computation=(
                "score = clamp(1 - stddev(torso_lean_deg) / 15, 0, 1) over phase frames."
            ),
            parameters={"stddev_denominator": 15.0},
            ideal_min=0.80,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
        _score_metric(
            metric_id="hip_stability",
            metric_name="hip_stability",
            phase_id="descent",
            description="Mid-hip lateral range stability score through descent.",
            required_landmarks=("left_hip", "right_hip"),
            computation=(
                "score = clamp(1 - (max(mid_hip.x) - min(mid_hip.x)) / 0.12, 0, 1)."
            ),
            parameters={"denominator": 0.12},
            ideal_min=0.76,
            base_moderate_deviation=0.09,
            base_severe_deviation=0.20,
        ),
        _score_metric(
            metric_id="repetition_consistency",
            metric_name="repetition_consistency",
            phase_id="ascent",
            description="Bilateral knee-angle symmetry score through ascent.",
            required_landmarks=(
                "left_hip",
                "right_hip",
                "left_knee",
                "right_knee",
                "left_ankle",
                "right_ankle",
            ),
            computation=(
                "score = clamp(1 - mean(abs(left_knee_angle - right_knee_angle)) / 35, 0, 1)."
            ),
            parameters={"angle_difference_denominator": 35.0},
            ideal_min=0.80,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
        _score_metric(
            metric_id="torso_alignment",
            metric_name="torso_alignment",
            phase_id="ascent",
            description="Torso lean consistency score through ascent.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_hip",
                "right_hip",
            ),
            computation=(
                "score = clamp(1 - stddev(torso_lean_deg) / 15, 0, 1) over phase frames."
            ),
            parameters={"stddev_denominator": 15.0},
            ideal_min=0.80,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
    ),
)


SET_SHOT_FORM_CONTRACT = DrillPhase2AContract(
    drill_id="set_shot_form",
    drill_name="Set Shot Form",
    phases=("setup", "load", "release", "follow_through"),
    segmentation_formula=(
        "Use the dominant-side wrist trajectory. The release frame is the highest "
        "dominant wrist position (minimum y). The load frame is the lowest pre-release "
        "dominant wrist position (maximum y). Split setup before load and follow-through "
        "after release."
    ),
    segmentation_parameters={
        "min_valid_frames": 4.0,
        "setup_boundary_fraction": 0.50,
    },
    requires_dominant_side=True,
    metric_contracts=(
        _score_metric(
            metric_id="posture_accuracy",
            metric_name="posture_accuracy",
            phase_id="setup",
            description="Torso posture score from shoulder-midpoint to hip-midpoint lean.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_hip",
                "right_hip",
            ),
            computation=(
                "score = mean(clamp(1 - abs(torso_lean_deg - 8) / 28, 0, 1)); "
                "torso_lean_deg = atan2(abs(dx_mid_shoulder_hip), abs(dy_mid_shoulder_hip))."
            ),
            parameters={"target_lean_deg": 8.0, "denominator": 28.0},
            ideal_min=0.83,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
        _score_metric(
            metric_id="balance_stability",
            metric_name="balance_stability",
            phase_id="setup",
            description="Mid-hip lateral range stability score at setup.",
            required_landmarks=("left_hip", "right_hip"),
            computation=(
                "score = clamp(1 - (max(mid_hip.x) - min(mid_hip.x)) / 0.09, 0, 1)."
            ),
            parameters={"denominator": 0.09},
            ideal_min=0.79,
            base_moderate_deviation=0.09,
            base_severe_deviation=0.20,
        ),
        _score_metric(
            metric_id="elbow_angle_consistency",
            metric_name="elbow_angle_consistency",
            phase_id="load",
            description="Dominant elbow set-angle score near 90 degrees during load.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_elbow",
                "right_elbow",
                "left_wrist",
                "right_wrist",
            ),
            computation=(
                "score = mean(clamp(1 - abs(angle(shoulder,elbow,wrist) - 90) / 50, 0, 1)) "
                "for the dominant arm."
            ),
            parameters={"target_angle_deg": 90.0, "denominator": 50.0},
            ideal_min=0.80,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
        _score_metric(
            metric_id="shooting_alignment",
            metric_name="shooting_alignment",
            phase_id="load",
            description="Dominant shoulder-elbow-wrist vertical stack score during load.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_elbow",
                "right_elbow",
                "left_wrist",
                "right_wrist",
            ),
            computation=(
                "score = mean(clamp(1 - (abs(elbow.x - shoulder.x) + abs(wrist.x - elbow.x)) "
                "/ max(0.65 * shoulder_width, 0.05), 0, 1)) for the dominant arm."
            ),
            parameters={"shoulder_width_factor": 0.65, "min_denominator": 0.05},
            ideal_min=0.84,
            base_moderate_deviation=0.07,
            base_severe_deviation=0.16,
        ),
        _score_metric(
            metric_id="shooting_alignment",
            metric_name="shooting_alignment",
            phase_id="release",
            description="Dominant shoulder-elbow-wrist vertical stack score at release.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_elbow",
                "right_elbow",
                "left_wrist",
                "right_wrist",
            ),
            computation=(
                "score = mean(clamp(1 - (abs(elbow.x - shoulder.x) + abs(wrist.x - elbow.x)) "
                "/ max(0.65 * shoulder_width, 0.05), 0, 1)) for the dominant arm."
            ),
            parameters={"shoulder_width_factor": 0.65, "min_denominator": 0.05},
            ideal_min=0.84,
            base_moderate_deviation=0.07,
            base_severe_deviation=0.16,
        ),
        _score_metric(
            metric_id="shoulder_control",
            metric_name="shoulder_control",
            phase_id="release",
            description="Dominant shoulder-over-hip stack score at release.",
            required_landmarks=("left_shoulder", "right_shoulder", "left_hip", "right_hip"),
            computation=(
                "score = mean(clamp(1 - abs(dominant_shoulder.x - dominant_hip.x) / 0.18, 0, 1))."
            ),
            parameters={"denominator": 0.18},
            ideal_min=0.81,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
        _score_metric(
            metric_id="elbow_angle_consistency",
            metric_name="elbow_angle_consistency",
            phase_id="follow_through",
            description="Dominant elbow extension score near 165 degrees after release.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_elbow",
                "right_elbow",
                "left_wrist",
                "right_wrist",
            ),
            computation=(
                "score = mean(clamp(1 - abs(angle(shoulder,elbow,wrist) - 165) / 45, 0, 1)) "
                "for the dominant arm."
            ),
            parameters={"target_angle_deg": 165.0, "denominator": 45.0},
            ideal_min=0.80,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
        _score_metric(
            metric_id="balance_stability",
            metric_name="balance_stability",
            phase_id="follow_through",
            description="Mid-hip lateral range stability score after release.",
            required_landmarks=("left_hip", "right_hip"),
            computation=(
                "score = clamp(1 - (max(mid_hip.x) - min(mid_hip.x)) / 0.09, 0, 1)."
            ),
            parameters={"denominator": 0.09},
            ideal_min=0.79,
            base_moderate_deviation=0.09,
            base_severe_deviation=0.20,
        ),
    ),
)


DUMBBELL_SHOULDER_PRESS_CONTRACT = DrillPhase2AContract(
    drill_id="dumbbell_shoulder_press",
    drill_name="Dumbbell Shoulder Press",
    phases=("setup", "press", "lockout", "return"),
    segmentation_formula=(
        "Use bilateral wrist vertical trajectory. The lockout frame is the highest "
        "average wrist position (minimum y). The press boundary is the first "
        "pre-lockout frame with material upward wrist motion. The return boundary "
        "is the first post-lockout frame with material downward wrist motion."
    ),
    segmentation_parameters={
        "min_valid_frames": 4.0,
        "setup_window_frames": 5.0,
        "min_wrist_motion_delta": 0.03,
        "boundary_min_delta": 0.02,
        "boundary_delta_ratio": 0.25,
        "press_fallback_fraction": 0.25,
        "return_fallback_fraction": 0.33,
    },
    requires_dominant_side=False,
    metric_contracts=(
        _score_metric(
            metric_id="posture_accuracy",
            metric_name="posture_accuracy",
            phase_id="setup",
            description="Stacked torso setup score before pressing.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_hip",
                "right_hip",
            ),
            computation=(
                "score = mean(clamp(1 - abs(torso_lean_deg - 4) / 18, 0, 1)) "
                "over setup frames."
            ),
            parameters={"target_lean_deg": 4.0, "denominator": 18.0},
            ideal_min=0.83,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
        _score_metric(
            metric_id="elbow_extension",
            metric_name="elbow_extension",
            phase_id="press",
            description="Bilateral elbow extension toward the overhead press path.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_elbow",
                "right_elbow",
                "left_wrist",
                "right_wrist",
            ),
            computation=(
                "score = mean(clamp(1 - abs(mean(angle(shoulder,elbow,wrist)) - 145) "
                "/ 55, 0, 1)) computed bilaterally."
            ),
            parameters={"target_angle_deg": 145.0, "denominator": 55.0},
            ideal_min=0.78,
            base_moderate_deviation=0.09,
            base_severe_deviation=0.20,
        ),
        _score_metric(
            metric_id="wrist_elbow_alignment",
            metric_name="wrist_elbow_alignment",
            phase_id="press",
            description="Wrists stacked over elbows through the press.",
            required_landmarks=(
                "left_elbow",
                "right_elbow",
                "left_wrist",
                "right_wrist",
            ),
            computation=(
                "score = mean(clamp(1 - mean(abs(wrist.x - elbow.x)) / 0.12, 0, 1)) "
                "computed bilaterally."
            ),
            parameters={"denominator": 0.12},
            ideal_min=0.80,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
        _score_metric(
            metric_id="torso_alignment",
            metric_name="torso_alignment",
            phase_id="press",
            description="Torso lean consistency while pressing.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_hip",
                "right_hip",
            ),
            computation=(
                "score = clamp(1 - stddev(torso_lean_deg) / 10, 0, 1) over phase frames."
            ),
            parameters={"stddev_denominator": 10.0},
            ideal_min=0.82,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
        _score_metric(
            metric_id="lockout_control",
            metric_name="lockout_control",
            phase_id="lockout",
            description="Controlled overhead lockout from elbow extension and wrist height stability.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_elbow",
                "right_elbow",
                "left_wrist",
                "right_wrist",
            ),
            computation=(
                "score = mean(elbow_extension_score, wrist_height_stability_score); "
                "elbow_extension_score = clamp(1 - abs(avg_elbow_angle - 168) / 25, 0, 1); "
                "wrist_height_stability_score = clamp(1 - wrist_y_range / 0.04, 0, 1)."
            ),
            parameters={
                "target_angle_deg": 168.0,
                "angle_denominator": 25.0,
                "wrist_y_denominator": 0.04,
            },
            ideal_min=0.82,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
        _score_metric(
            metric_id="shoulder_symmetry",
            metric_name="shoulder_symmetry",
            phase_id="lockout",
            description="Left-right shoulder and wrist height symmetry at lockout.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_wrist",
                "right_wrist",
            ),
            computation=(
                "score = mean(clamp(1 - (abs(left_shoulder.y - right_shoulder.y) "
                "+ abs(left_wrist.y - right_wrist.y)) / 0.10, 0, 1))."
            ),
            parameters={"denominator": 0.10},
            ideal_min=0.80,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
        _score_metric(
            metric_id="wrist_elbow_alignment",
            metric_name="wrist_elbow_alignment",
            phase_id="return",
            description="Wrists stay stacked over elbows while returning to start.",
            required_landmarks=(
                "left_elbow",
                "right_elbow",
                "left_wrist",
                "right_wrist",
            ),
            computation=(
                "score = mean(clamp(1 - mean(abs(wrist.x - elbow.x)) / 0.12, 0, 1)) "
                "computed bilaterally."
            ),
            parameters={"denominator": 0.12},
            ideal_min=0.78,
            base_moderate_deviation=0.09,
            base_severe_deviation=0.20,
        ),
        _score_metric(
            metric_id="torso_alignment",
            metric_name="torso_alignment",
            phase_id="return",
            description="Torso lean consistency while returning from overhead.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_hip",
                "right_hip",
            ),
            computation=(
                "score = clamp(1 - stddev(torso_lean_deg) / 10, 0, 1) over phase frames."
            ),
            parameters={"stddev_denominator": 10.0},
            ideal_min=0.82,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
    ),
)


DEFENSIVE_STANCE_CONTRACT = DrillPhase2AContract(
    drill_id="defensive_stance",
    drill_name="Defensive Stance",
    phases=("setup", "hold", "recovery"),
    segmentation_formula=(
        "Use bilateral knee angle. Setup begins at the first valid frame. Hold begins "
        "when average knee angle drops materially from setup. Recovery begins when "
        "average knee angle rises materially from the low stance position."
    ),
    segmentation_parameters={
        "min_valid_frames": 3.0,
        "setup_window_frames": 5.0,
        "min_knee_motion_delta_deg": 3.0,
        "boundary_min_delta_deg": 5.0,
        "boundary_delta_ratio": 0.35,
        "hold_fallback_fraction": 0.33,
        "recovery_fallback_fraction": 0.33,
    },
    requires_dominant_side=False,
    metric_contracts=(
        _score_metric(
            metric_id="stance_width_control",
            metric_name="stance_width_control",
            phase_id="setup",
            description="Ankle stance width relative to shoulder width at setup.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_ankle",
                "right_ankle",
            ),
            computation=(
                "score = mean(clamp(1 - abs((ankle_width / shoulder_width) - 1.30) "
                "/ 0.45, 0, 1))."
            ),
            parameters={
                "target_ratio": 1.30,
                "denominator": 0.45,
                "min_shoulder_width": 0.05,
            },
            ideal_min=0.81,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
        _score_metric(
            metric_id="posture_accuracy",
            metric_name="posture_accuracy",
            phase_id="setup",
            description="Torso angle score for the initial defensive stance.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_hip",
                "right_hip",
            ),
            computation=(
                "score = mean(clamp(1 - abs(torso_lean_deg - 14) / 25, 0, 1)) "
                "over setup frames."
            ),
            parameters={"target_lean_deg": 14.0, "denominator": 25.0},
            ideal_min=0.80,
            base_moderate_deviation=0.09,
            base_severe_deviation=0.20,
        ),
        _score_metric(
            metric_id="knee_flexion",
            metric_name="knee_flexion",
            phase_id="hold",
            description="Loaded knee flexion score while holding the stance.",
            required_landmarks=(
                "left_hip",
                "right_hip",
                "left_knee",
                "right_knee",
                "left_ankle",
                "right_ankle",
            ),
            computation=(
                "score = mean(clamp(1 - abs(avg_knee_angle - 115) / 45, 0, 1)) "
                "computed bilaterally."
            ),
            parameters={"target_angle_deg": 115.0, "denominator": 45.0},
            ideal_min=0.80,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
        _score_metric(
            metric_id="stance_width_control",
            metric_name="stance_width_control",
            phase_id="hold",
            description="Stance width control while maintaining the defensive base.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_ankle",
                "right_ankle",
            ),
            computation=(
                "score = mean(clamp(1 - abs((ankle_width / shoulder_width) - 1.30) "
                "/ 0.45, 0, 1))."
            ),
            parameters={
                "target_ratio": 1.30,
                "denominator": 0.45,
                "min_shoulder_width": 0.05,
            },
            ideal_min=0.82,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
        _score_metric(
            metric_id="hip_level_stability",
            metric_name="hip_level_stability",
            phase_id="hold",
            description="Left-right hip height stability while staying low.",
            required_landmarks=("left_hip", "right_hip"),
            computation=(
                "score = mean(clamp(1 - abs(left_hip.y - right_hip.y) / 0.08, 0, 1))."
            ),
            parameters={"denominator": 0.08},
            ideal_min=0.80,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
        _score_metric(
            metric_id="torso_alignment",
            metric_name="torso_alignment",
            phase_id="hold",
            description="Torso lean consistency while holding the stance.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_hip",
                "right_hip",
            ),
            computation=(
                "score = clamp(1 - stddev(torso_lean_deg) / 10, 0, 1) over phase frames."
            ),
            parameters={"stddev_denominator": 10.0},
            ideal_min=0.81,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
        _score_metric(
            metric_id="balance_stability",
            metric_name="balance_stability",
            phase_id="recovery",
            description="Lateral balance control during recovery from stance.",
            required_landmarks=("left_hip", "right_hip"),
            computation=(
                "score = clamp(1 - (max(mid_hip.x) - min(mid_hip.x)) / 0.10, 0, 1)."
            ),
            parameters={"denominator": 0.10},
            ideal_min=0.80,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
        _score_metric(
            metric_id="knee_flexion",
            metric_name="knee_flexion",
            phase_id="recovery",
            description="Controlled recovery knee angle without abrupt posture loss.",
            required_landmarks=(
                "left_hip",
                "right_hip",
                "left_knee",
                "right_knee",
                "left_ankle",
                "right_ankle",
            ),
            computation=(
                "score = mean(clamp(1 - abs(avg_knee_angle - 135) / 55, 0, 1)) "
                "computed bilaterally."
            ),
            parameters={"target_angle_deg": 135.0, "denominator": 55.0},
            ideal_min=0.78,
            base_moderate_deviation=0.09,
            base_severe_deviation=0.20,
        ),
    ),
)


INSTEP_PASS_CONTRACT = DrillPhase2AContract(
    drill_id="instep_pass",
    drill_name="Instep Pass",
    phases=("setup", "backswing", "contact", "follow_through"),
    segmentation_formula=(
        "Use the dominant kicking-leg hip-knee-ankle angle and support-foot proxy. "
        "Backswing is the frame of peak kicking-knee flexion. Contact is the post-backswing "
        "frame where the kicking ankle is closest to the support ankle. Follow-through "
        "continues from contact to the final valid frame."
    ),
    segmentation_parameters={
        "min_valid_frames": 4.0,
        "setup_window_frames": 5.0,
        "min_kicking_knee_motion_delta_deg": 3.0,
        "boundary_min_delta_deg": 5.0,
        "boundary_delta_ratio": 0.25,
        "backswing_fallback_fraction": 0.33,
    },
    requires_dominant_side=False,
    metric_contracts=(
        _score_metric(
            metric_id="plant_foot_alignment_ratio",
            metric_name="plant_foot_alignment_ratio",
            phase_id="setup",
            description="Support-foot placement ratio relative to hip center and shoulder width.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_hip",
                "right_hip",
                "left_ankle",
                "right_ankle",
            ),
            computation=(
                "support_side = opposite(dominant_side); ratio = "
                "abs(support_ankle.x - mid_hip.x) / max(shoulder_width, min_reference); "
                "score = mean(clamp(1 - abs(ratio - target_ratio) / denominator, 0, 1))."
            ),
            parameters={
                "target_ratio": 0.55,
                "denominator": 0.40,
                "min_reference": 0.05,
            },
            ideal_min=0.78,
            base_moderate_deviation=0.09,
            base_severe_deviation=0.20,
        ),
        _score_metric(
            metric_id="instep_backswing_knee_angle",
            metric_name="instep_backswing_knee_angle",
            phase_id="backswing",
            description="Kicking-knee flexion angle score at the backswing phase.",
            required_landmarks=(
                "left_hip",
                "right_hip",
                "left_knee",
                "right_knee",
                "left_ankle",
                "right_ankle",
            ),
            computation=(
                "score = mean(clamp(1 - abs(angle(kicking_hip,kicking_knee,kicking_ankle) "
                "- target_angle_deg) / denominator, 0, 1))."
            ),
            parameters={"target_angle_deg": 95.0, "denominator": 45.0},
            ideal_min=0.78,
            base_moderate_deviation=0.09,
            base_severe_deviation=0.20,
        ),
        _score_metric(
            metric_id="instep_contact_extension",
            metric_name="instep_contact_extension",
            phase_id="contact",
            description="Kicking-leg knee extension score through contact.",
            required_landmarks=(
                "left_hip",
                "right_hip",
                "left_knee",
                "right_knee",
                "left_ankle",
                "right_ankle",
            ),
            computation=(
                "score = mean(clamp(1 - abs(angle(kicking_hip,kicking_knee,kicking_ankle) "
                "- target_angle_deg) / denominator, 0, 1))."
            ),
            parameters={"target_angle_deg": 160.0, "denominator": 35.0},
            ideal_min=0.80,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
        _score_metric(
            metric_id="instep_torso_tilt",
            metric_name="instep_torso_tilt",
            phase_id="contact",
            description="Torso tilt score from shoulder-midpoint to hip-midpoint at contact.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_hip",
                "right_hip",
            ),
            computation=(
                "score = mean(clamp(1 - abs(torso_lean_deg - target_tilt_deg) "
                "/ denominator, 0, 1)); torso_lean_deg = atan2(abs(dx_mid_shoulder_hip), "
                "abs(dy_mid_shoulder_hip))."
            ),
            parameters={"target_tilt_deg": 10.0, "denominator": 25.0},
            ideal_min=0.79,
            base_moderate_deviation=0.09,
            base_severe_deviation=0.20,
        ),
        _score_metric(
            metric_id="instep_follow_through_stability",
            metric_name="instep_follow_through_stability",
            phase_id="follow_through",
            description="Kicking-foot trajectory stability after contact.",
            required_landmarks=("left_ankle", "right_ankle"),
            computation=(
                "x_score = clamp(1 - range(kicking_ankle.x) / x_denominator, 0, 1); "
                "y_score = clamp(1 - range(kicking_ankle.y) / y_denominator, 0, 1); "
                "score = mean(x_score, y_score)."
            ),
            parameters={"x_denominator": 0.24, "y_denominator": 0.20},
            ideal_min=0.77,
            base_moderate_deviation=0.10,
            base_severe_deviation=0.22,
        ),
    ),
)


BASIC_SHOOTING_FORM_CONTRACT = DrillPhase2AContract(
    drill_id="basic_shooting_form",
    drill_name="Basic Shooting Form",
    phases=("setup", "load", "swing", "contact", "follow_through"),
    segmentation_formula=(
        "Use the dominant kicking-leg knee angle and support-foot proxy. Load is peak "
        "kicking-knee flexion, swing spans from load to the first post-load peak extension, "
        "and contact is the post-load frame where the kicking ankle is closest to the support ankle."
    ),
    segmentation_parameters={
        "min_valid_frames": 5.0,
        "setup_window_frames": 5.0,
        "min_pre_contact_frames": 2.0,
        "min_kicking_knee_motion_delta_deg": 3.0,
        "boundary_min_delta_deg": 5.0,
        "boundary_delta_ratio": 0.25,
        "load_fallback_fraction": 0.33,
    },
    requires_dominant_side=False,
    metric_contracts=(
        _score_metric(
            metric_id="support_foot_distance_ratio",
            metric_name="support_foot_distance_ratio",
            phase_id="setup",
            description="Support-foot distance from hip center relative to shoulder width.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_hip",
                "right_hip",
                "left_ankle",
                "right_ankle",
            ),
            computation=(
                "support_side = opposite(dominant_side); ratio = "
                "abs(support_ankle.x - mid_hip.x) / max(shoulder_width, min_reference); "
                "score = mean(clamp(1 - abs(ratio - target_ratio) / denominator, 0, 1))."
            ),
            parameters={
                "target_ratio": 0.60,
                "denominator": 0.42,
                "min_reference": 0.05,
            },
            ideal_min=0.78,
            base_moderate_deviation=0.09,
            base_severe_deviation=0.20,
        ),
        _score_metric(
            metric_id="shooting_knee_load",
            metric_name="shooting_knee_load",
            phase_id="load",
            description="Kicking-knee loading flexion score before the swing.",
            required_landmarks=(
                "left_hip",
                "right_hip",
                "left_knee",
                "right_knee",
                "left_ankle",
                "right_ankle",
            ),
            computation=(
                "score = mean(clamp(1 - abs(angle(kicking_hip,kicking_knee,kicking_ankle) "
                "- target_angle_deg) / denominator, 0, 1))."
            ),
            parameters={"target_angle_deg": 105.0, "denominator": 50.0},
            ideal_min=0.78,
            base_moderate_deviation=0.09,
            base_severe_deviation=0.20,
        ),
        _score_metric(
            metric_id="shooting_swing_velocity",
            metric_name="shooting_swing_velocity",
            phase_id="swing",
            description="Frame-to-frame kicking-ankle displacement velocity proxy.",
            required_landmarks=("left_ankle", "right_ankle"),
            computation=(
                "velocity_proxy = mean(distance(kicking_ankle[t], kicking_ankle[t-1])); "
                "score = clamp(velocity_proxy / target_velocity, 0, 1)."
            ),
            parameters={"target_velocity": 0.055},
            ideal_min=0.76,
            base_moderate_deviation=0.10,
            base_severe_deviation=0.22,
        ),
        _score_metric(
            metric_id="shooting_contact_extension",
            metric_name="shooting_contact_extension",
            phase_id="contact",
            description="Kicking-leg extension score at shooting contact.",
            required_landmarks=(
                "left_hip",
                "right_hip",
                "left_knee",
                "right_knee",
                "left_ankle",
                "right_ankle",
            ),
            computation=(
                "score = mean(clamp(1 - abs(angle(kicking_hip,kicking_knee,kicking_ankle) "
                "- target_angle_deg) / denominator, 0, 1))."
            ),
            parameters={"target_angle_deg": 165.0, "denominator": 35.0},
            ideal_min=0.80,
            base_moderate_deviation=0.08,
            base_severe_deviation=0.18,
        ),
        _score_metric(
            metric_id="support_foot_distance_ratio",
            metric_name="support_foot_distance_ratio",
            phase_id="contact",
            description="Support-foot distance from hip center at shooting contact.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_hip",
                "right_hip",
                "left_ankle",
                "right_ankle",
            ),
            computation=(
                "support_side = opposite(dominant_side); ratio = "
                "abs(support_ankle.x - mid_hip.x) / max(shoulder_width, min_reference); "
                "score = mean(clamp(1 - abs(ratio - target_ratio) / denominator, 0, 1))."
            ),
            parameters={
                "target_ratio": 0.60,
                "denominator": 0.42,
                "min_reference": 0.05,
            },
            ideal_min=0.78,
            base_moderate_deviation=0.09,
            base_severe_deviation=0.20,
        ),
        _score_metric(
            metric_id="torso_rotation_stability",
            metric_name="torso_rotation_stability",
            phase_id="follow_through",
            description="Shoulder-hip lateral offset stability during follow-through.",
            required_landmarks=(
                "left_shoulder",
                "right_shoulder",
                "left_hip",
                "right_hip",
            ),
            computation=(
                "offset = mid_shoulder.x - mid_hip.x; "
                "score = clamp(1 - stddev(offset) / denominator, 0, 1)."
            ),
            parameters={"denominator": 0.08},
            ideal_min=0.78,
            base_moderate_deviation=0.09,
            base_severe_deviation=0.20,
        ),
        _score_metric(
            metric_id="shooting_balance",
            metric_name="shooting_balance",
            phase_id="follow_through",
            description="Mid-hip and support-foot stability after the strike.",
            required_landmarks=("left_hip", "right_hip", "left_ankle", "right_ankle"),
            computation=(
                "mid_hip_score = clamp(1 - range(mid_hip.x) / hip_x_denominator, 0, 1); "
                "support_ankle_score = clamp(1 - range(support_ankle.x) / support_x_denominator, 0, 1); "
                "score = mean(mid_hip_score, support_ankle_score)."
            ),
            parameters={"hip_x_denominator": 0.12, "support_x_denominator": 0.08},
            ideal_min=0.78,
            base_moderate_deviation=0.09,
            base_severe_deviation=0.20,
        ),
    ),
)


PHASE2A_CONTRACTS_BY_DRILL_NAME: dict[str, DrillPhase2AContract] = {
    BODYWEIGHT_SQUAT_CONTRACT.drill_name: BODYWEIGHT_SQUAT_CONTRACT,
    SET_SHOT_FORM_CONTRACT.drill_name: SET_SHOT_FORM_CONTRACT,
    DUMBBELL_SHOULDER_PRESS_CONTRACT.drill_name: DUMBBELL_SHOULDER_PRESS_CONTRACT,
    DEFENSIVE_STANCE_CONTRACT.drill_name: DEFENSIVE_STANCE_CONTRACT,
    INSTEP_PASS_CONTRACT.drill_name: INSTEP_PASS_CONTRACT,
    BASIC_SHOOTING_FORM_CONTRACT.drill_name: BASIC_SHOOTING_FORM_CONTRACT,
}


def get_phase2a_contract(drill_name: str) -> DrillPhase2AContract | None:
    return PHASE2A_CONTRACTS_BY_DRILL_NAME.get(drill_name)
