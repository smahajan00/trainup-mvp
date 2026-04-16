from __future__ import annotations

from app.engines.cognition_engine.drill_evaluators.base import BaseDrillEvaluator


class BodyweightSquatEvaluator(BaseDrillEvaluator):
    def __init__(self) -> None:
        super().__init__(
            evaluator_name="BodyweightSquatEvaluator",
            metric_weights={
                "posture_accuracy": {
                    "movement_control": 0.30,
                    "torso_stack": 0.30,
                    "balance_control": 0.15,
                    "coverage": 0.10,
                    "confidence": 0.15,
                },
                "knee_alignment_score": {
                    "knee_track": 0.55,
                    "hip_alignment": 0.15,
                    "balance_control": 0.20,
                    "coverage": 0.10,
                },
                "torso_alignment": {
                    "torso_stack": 0.60,
                    "movement_control": 0.20,
                    "motion_stability": 0.20,
                },
                "hip_stability": {
                    "hip_alignment": 0.45,
                    "balance_control": 0.25,
                    "motion_stability": 0.20,
                    "payload_completeness": 0.10,
                },
                "repetition_consistency": {
                    "repeatability": 0.55,
                    "tempo": 0.25,
                    "frame_consistency": 0.20,
                },
            },
            metric_biases={
                "knee_alignment_score": -0.14,
                "torso_alignment": -0.12,
                "repetition_consistency": -0.08,
            },
        )
