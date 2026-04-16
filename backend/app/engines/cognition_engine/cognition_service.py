from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.engines.cognition_engine.evaluators import build_diagnostic_flags
from app.engines.cognition_engine.metrics import (
    compute_coverage_score,
    compute_frame_consistency_score,
    compute_motion_stability_score,
    compute_payload_completeness_score,
)
from app.schemas.session import (
    CognitionDerivedMetrics,
    CognitionProcessingReadiness,
    CognitionResult,
    PerceptionResult,
)


@dataclass
class CognitionService:
    def analyze_perception_payload(
        self,
        *,
        session_id: UUID,
        drill_id: UUID,
        perception_result: PerceptionResult,
    ) -> CognitionResult:
        frame_count = perception_result.processing_summary.frame_count
        available_joint_count = perception_result.derived_motion_features.available_joint_count

        readiness = CognitionProcessingReadiness(
            payload_usable=frame_count > 0 and available_joint_count >= 6,
            minimum_frames_met=frame_count >= 60,
        )

        metrics = CognitionDerivedMetrics(
            frame_consistency_score=compute_frame_consistency_score(perception_result),
            coverage_score=compute_coverage_score(perception_result),
            motion_stability_score=compute_motion_stability_score(perception_result),
            payload_completeness_score=compute_payload_completeness_score(
                perception_result
            ),
        )

        return CognitionResult(
            analysis_mode="scaffold",
            session_id=session_id,
            drill_id=drill_id,
            processing_readiness=readiness,
            derived_metrics=metrics,
            diagnostic_flags=build_diagnostic_flags(
                payload=perception_result,
                metrics=metrics,
                minimum_frames_met=readiness.minimum_frames_met,
            ),
        )
