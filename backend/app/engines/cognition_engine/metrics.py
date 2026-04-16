from __future__ import annotations

from statistics import mean
from typing import Any

from app.schemas.session import PerceptionResult

Coordinate = tuple[float, float, float]


def clamp_score(value: float) -> float:
    return round(max(0.0, min(value, 1.0)), 3)


def average_frame_confidence(payload: PerceptionResult) -> float:
    if not payload.keypoint_series:
        return 0.0
    return mean(frame.confidence for frame in payload.keypoint_series)


def compute_frame_consistency_score(payload: PerceptionResult) -> float:
    """Blend frame confidence with missing-frame pressure for a stable scaffold score."""
    confidence = average_frame_confidence(payload)
    missing_ratio = payload.derived_motion_features.missing_frame_ratio
    return clamp_score((confidence * 0.7) + ((1 - missing_ratio) * 0.3))


def compute_coverage_score(payload: PerceptionResult) -> float:
    """Coverage rewards joint availability and penalizes missing frames."""
    joint_coverage = min(payload.derived_motion_features.available_joint_count / 12, 1.0)
    missing_ratio = payload.derived_motion_features.missing_frame_ratio
    return clamp_score((joint_coverage * 0.55) + ((1 - missing_ratio) * 0.45))


def compute_motion_stability_score(payload: PerceptionResult) -> float:
    """Stability is anchored in the perception hint with a smaller confidence correction."""
    stability_hint = payload.derived_motion_features.stability_hint
    confidence = average_frame_confidence(payload)
    return clamp_score((stability_hint * 0.75) + (confidence * 0.25))


def compute_payload_completeness_score(payload: PerceptionResult) -> float:
    """Completeness combines sampled-frame availability, joint coverage, and missing-frame rate."""
    frame_count = payload.processing_summary.frame_count
    sampled_frames = len(payload.keypoint_series)
    sampled_ratio = sampled_frames / min(frame_count, 12) if frame_count else 0.0
    joint_coverage = min(payload.derived_motion_features.available_joint_count / 12, 1.0)
    missing_ratio = payload.derived_motion_features.missing_frame_ratio
    return clamp_score(
        (sampled_ratio * 0.4) + (joint_coverage * 0.35) + ((1 - missing_ratio) * 0.25)
    )


def _mean_or_none(values: list[float]) -> float | None:
    filtered = [value for value in values if value is not None]
    if not filtered:
        return None
    return mean(filtered)


def _average_coordinate(payload: PerceptionResult, label: str) -> Coordinate | None:
    coordinates = [
        frame.keypoints[label]
        for frame in payload.keypoint_series
        if label in frame.keypoints
    ]
    if not coordinates:
        return None
    return (
        mean(point.x for point in coordinates),
        mean(point.y for point in coordinates),
        mean(point.z for point in coordinates),
    )


def _center_of(*coords: Coordinate | None) -> Coordinate | None:
    available = [coord for coord in coords if coord is not None]
    if not available:
        return None
    return (
        mean(coord[0] for coord in available),
        mean(coord[1] for coord in available),
        mean(coord[2] for coord in available),
    )


def _center_alignment_score(
    source: Coordinate | None,
    target: Coordinate | None,
    *,
    axis: str = "x",
    tolerance: float = 0.12,
) -> float | None:
    if source is None or target is None:
        return None

    axis_index = {"x": 0, "y": 1, "z": 2}[axis]
    deviation = abs(source[axis_index] - target[axis_index])
    return clamp_score(1 - (deviation / tolerance))


def _chain_alignment_score(
    origin: Coordinate | None,
    middle: Coordinate | None,
    end: Coordinate | None,
    *,
    axis: str = "x",
    tolerance: float = 0.08,
) -> float | None:
    if origin is None or middle is None or end is None:
        return None

    axis_index = {"x": 0, "y": 1, "z": 2}[axis]
    expected = (origin[axis_index] + end[axis_index]) / 2
    deviation = abs(middle[axis_index] - expected)
    return clamp_score(1 - (deviation / tolerance))


def _pair_level_score(
    left: Coordinate | None,
    right: Coordinate | None,
    *,
    axis: str = "y",
    tolerance: float = 0.05,
) -> float | None:
    if left is None or right is None:
        return None

    axis_index = {"x": 0, "y": 1, "z": 2}[axis]
    deviation = abs(left[axis_index] - right[axis_index])
    return clamp_score(1 - (deviation / tolerance))


def _stance_width_control_score(
    payload: PerceptionResult,
    reference_payload: dict[str, Any],
) -> float | None:
    left_ankle = _average_coordinate(payload, "left_ankle")
    right_ankle = _average_coordinate(payload, "right_ankle")
    left_hip = _average_coordinate(payload, "left_hip")
    right_hip = _average_coordinate(payload, "right_hip")
    if left_ankle is None or right_ankle is None or left_hip is None or right_hip is None:
        return None

    ankle_width = abs(right_ankle[0] - left_ankle[0])
    hip_width = max(abs(right_hip[0] - left_hip[0]), 0.01)
    ratio = ankle_width / hip_width
    ideal_ranges = reference_payload.get("ideal_ranges", {}) if reference_payload else {}
    ratio_range = ideal_ranges.get("stance_width_ratio", {})
    minimum = float(ratio_range.get("min", 1.0))
    maximum = float(ratio_range.get("max", 1.35))
    if minimum <= ratio <= maximum:
        return 1.0
    target = minimum if ratio < minimum else maximum
    deviation = abs(ratio - target)
    return clamp_score(1 - (deviation / 0.45))


def _shooting_line_score(payload: PerceptionResult) -> float | None:
    left_score = _chain_alignment_score(
        _average_coordinate(payload, "left_shoulder"),
        _average_coordinate(payload, "left_elbow"),
        _average_coordinate(payload, "left_wrist"),
        axis="x",
        tolerance=0.07,
    )
    right_score = _chain_alignment_score(
        _average_coordinate(payload, "right_shoulder"),
        _average_coordinate(payload, "right_elbow"),
        _average_coordinate(payload, "right_wrist"),
        axis="x",
        tolerance=0.07,
    )
    score = _mean_or_none([left_score, right_score])
    if score is None:
        return None
    return clamp_score(score)


def _tempo_control_score(payload: PerceptionResult) -> float:
    frame_consistency = compute_frame_consistency_score(payload)
    completeness = compute_payload_completeness_score(payload)
    fps_component = min(payload.processing_summary.fps_estimate / 30, 1.0)
    return clamp_score(
        (frame_consistency * 0.45) + (completeness * 0.35) + (fps_component * 0.2)
    )


def _movement_control_signal(payload: PerceptionResult) -> float:
    return clamp_score(
        (
            compute_frame_consistency_score(payload)
            + compute_motion_stability_score(payload)
            + compute_payload_completeness_score(payload)
        )
        / 3
    )


def compute_common_signals(
    payload: PerceptionResult,
    reference_payload: dict[str, Any],
) -> dict[str, float]:
    frame_consistency = compute_frame_consistency_score(payload)
    coverage = compute_coverage_score(payload)
    motion_stability = compute_motion_stability_score(payload)
    completeness = compute_payload_completeness_score(payload)
    tempo = _tempo_control_score(payload)
    movement_control = _movement_control_signal(payload)

    left_shoulder = _average_coordinate(payload, "left_shoulder")
    right_shoulder = _average_coordinate(payload, "right_shoulder")
    left_hip = _average_coordinate(payload, "left_hip")
    right_hip = _average_coordinate(payload, "right_hip")
    left_knee = _average_coordinate(payload, "left_knee")
    right_knee = _average_coordinate(payload, "right_knee")
    left_ankle = _average_coordinate(payload, "left_ankle")
    right_ankle = _average_coordinate(payload, "right_ankle")
    sternum = _average_coordinate(payload, "sternum_center")
    pelvis = _average_coordinate(payload, "pelvis_center")

    shoulder_center = _center_of(left_shoulder, right_shoulder, sternum)
    hip_center = _center_of(left_hip, right_hip, pelvis)
    ankle_center = _center_of(left_ankle, right_ankle)

    torso_stack = _center_alignment_score(
        shoulder_center,
        hip_center,
        axis="x",
        tolerance=0.11,
    )
    hip_alignment = _center_alignment_score(
        hip_center,
        ankle_center,
        axis="x",
        tolerance=0.12,
    )

    knee_track = _mean_or_none(
        [
            _chain_alignment_score(left_hip, left_knee, left_ankle, tolerance=0.09),
            _chain_alignment_score(right_hip, right_knee, right_ankle, tolerance=0.09),
        ]
    )
    elbow_track = _mean_or_none(
        [
            _chain_alignment_score(
                _average_coordinate(payload, "left_shoulder"),
                _average_coordinate(payload, "left_elbow"),
                _average_coordinate(payload, "left_wrist"),
                tolerance=0.08,
            ),
            _chain_alignment_score(
                _average_coordinate(payload, "right_shoulder"),
                _average_coordinate(payload, "right_elbow"),
                _average_coordinate(payload, "right_wrist"),
                tolerance=0.08,
            ),
        ]
    )

    shoulder_level = _pair_level_score(left_shoulder, right_shoulder, axis="y", tolerance=0.04)
    shoulder_stack = _mean_or_none([shoulder_level, torso_stack])
    ankle_level = _pair_level_score(left_ankle, right_ankle, axis="y", tolerance=0.05)
    centered_base = _center_alignment_score(ankle_center, hip_center, axis="x", tolerance=0.11)
    balance_control = _mean_or_none([motion_stability, ankle_level, centered_base])
    stance_width = _stance_width_control_score(payload, reference_payload)
    shooting_line = _shooting_line_score(payload)
    repeatability = _mean_or_none([frame_consistency, completeness, tempo])

    return {
        "confidence": clamp_score(average_frame_confidence(payload)),
        "frame_consistency": frame_consistency,
        "coverage": coverage,
        "motion_stability": motion_stability,
        "payload_completeness": completeness,
        "tempo": tempo,
        "movement_control": movement_control,
        "torso_stack": clamp_score(torso_stack or movement_control),
        "hip_alignment": clamp_score(hip_alignment or movement_control),
        "knee_track": clamp_score(knee_track or movement_control),
        "elbow_track": clamp_score(elbow_track or movement_control),
        "shoulder_stack": clamp_score(shoulder_stack or movement_control),
        "balance_control": clamp_score(balance_control or motion_stability),
        "stance_width": clamp_score(stance_width or coverage),
        "shooting_line": clamp_score(shooting_line or movement_control),
        "repeatability": clamp_score(repeatability or frame_consistency),
    }


def score_metric(
    *,
    signal_values: dict[str, float],
    weights: dict[str, float],
    bias: float = 0.0,
) -> float:
    if not weights:
        return clamp_score(signal_values.get("movement_control", 0.0) + bias)

    total_weight = sum(abs(weight) for weight in weights.values()) or 1.0
    weighted_score = sum(
        signal_values.get(signal_name, signal_values.get("movement_control", 0.0)) * weight
        for signal_name, weight in weights.items()
    )
    return clamp_score((weighted_score / total_weight) + bias)
