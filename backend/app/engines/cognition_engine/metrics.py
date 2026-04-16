from __future__ import annotations

from statistics import mean

from app.schemas.session import PerceptionResult


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
