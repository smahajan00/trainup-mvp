from __future__ import annotations

from enum import Enum

from app.models.enums import SeverityLevel

PHASE0_FORMULA_VERSION = "phase0_v0_1_0"
DEFAULT_PHASE_ID = "full_motion"


class MetricEvaluationState(str, Enum):
    GOOD = "GOOD"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"


_AFFECTED_BODY_PARTS_BY_METRIC: dict[str, str] = {
    "posture_accuracy": "trunk",
    "knee_alignment_score": "knees",
    "squat_depth": "lower_body",
    "elbow_angle_consistency": "elbows",
    "balance_stability": "balance",
    "torso_alignment": "trunk",
    "repetition_consistency": "full_body",
    "hip_stability": "hips",
    "shoulder_control": "shoulders",
    "shooting_alignment": "shooting_arm",
    "stance_width_control": "lower_body_base",
    "elbow_extension": "elbows",
    "wrist_elbow_alignment": "wrists_elbows",
    "lockout_control": "shoulders_elbows",
    "shoulder_symmetry": "shoulders",
    "knee_flexion": "knees",
    "hip_level_stability": "hips",
    "plant_foot_alignment_ratio": "support_foot",
    "instep_backswing_knee_angle": "kicking_knee",
    "instep_contact_extension": "kicking_leg",
    "instep_torso_tilt": "trunk",
    "instep_follow_through_stability": "kicking_leg",
    "support_foot_distance_ratio": "support_foot",
    "shooting_knee_load": "kicking_knee",
    "shooting_swing_velocity": "kicking_leg",
    "shooting_contact_extension": "kicking_leg",
    "torso_rotation_stability": "trunk",
    "shooting_balance": "balance",
}


def map_metric_state_to_severity_level(
    metric_state: MetricEvaluationState,
) -> SeverityLevel:
    if metric_state is MetricEvaluationState.SEVERE:
        return SeverityLevel.SEVERE
    if metric_state is MetricEvaluationState.MODERATE:
        return SeverityLevel.MODERATE
    return SeverityLevel.MINOR


def resolve_metric_phase_id(metric_name: str) -> str:
    return DEFAULT_PHASE_ID


def resolve_affected_body_part(metric_name: str) -> str:
    return _AFFECTED_BODY_PARTS_BY_METRIC.get(metric_name, "full_body")
