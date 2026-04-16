from __future__ import annotations

from app.schemas.session import CognitionDerivedMetrics, PerceptionResult


def build_diagnostic_flags(
    *,
    payload: PerceptionResult,
    metrics: CognitionDerivedMetrics,
    minimum_frames_met: bool,
) -> list[str]:
    flags = [
        "Scaffold cognition result; drill-specific biomechanical scoring comes next.",
    ]

    if not minimum_frames_met:
        flags.append(
            "Upload clip is short for richer drill-specific temporal evaluation."
        )

    if payload.derived_motion_features.missing_frame_ratio > 0.08:
        flags.append(
            "Payload coverage is limited; perception continuity should improve before final scoring."
        )

    if metrics.frame_consistency_score < 0.75:
        flags.append(
            "Frame confidence is moderate; positioning and lighting may need improvement."
        )

    return flags
