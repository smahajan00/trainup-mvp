from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.engines.cognition_engine.metrics import (
    compute_coverage_score,
    compute_frame_consistency_score,
    compute_motion_stability_score,
    compute_payload_completeness_score,
)
from app.engines.cognition_engine.registry import get_evaluator_for_drill
from app.models.drill import Drill
from app.models.training_session import TrainingSession
from app.schemas.session import (
    CognitionDerivedMetrics,
    CognitionProcessingReadiness,
    CognitionResult,
    DrillEvaluationResult,
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
            diagnostic_flags=self._build_diagnostic_flags(
                payload=perception_result,
                metrics=metrics,
                minimum_frames_met=readiness.minimum_frames_met,
            ),
        )

    def evaluate_drill_payload(
        self,
        *,
        perception_result: PerceptionResult,
        drill: Drill,
        session: TrainingSession,
    ) -> DrillEvaluationResult:
        evaluator = get_evaluator_for_drill(drill.drill_name)
        return evaluator.evaluate(
            perception_payload=perception_result,
            drill=drill,
            session=session,
        )

    @staticmethod
    def _build_diagnostic_flags(
        *,
        payload: PerceptionResult,
        metrics: CognitionDerivedMetrics,
        minimum_frames_met: bool,
    ) -> list[str]:
        flags = [
            "Clip review is ready.",
        ]

        if not minimum_frames_met:
            flags.append("A longer clip can improve review.")

        if payload.derived_motion_features.missing_frame_ratio > 0.08:
            flags.append("Some movement data is limited.")

        if metrics.frame_consistency_score < 0.75:
            flags.append("Lighting or framing may need work.")

        return flags
