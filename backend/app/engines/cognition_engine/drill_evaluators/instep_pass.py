from __future__ import annotations

from app.engines.cognition_engine.drill_evaluators.base import BaseDrillEvaluator


class InstepPassEvaluator(BaseDrillEvaluator):
    def __init__(self) -> None:
        super().__init__(
            evaluator_name="InstepPassEvaluator",
            metric_weights={
                "posture_accuracy": {
                    "movement_control": 0.30,
                    "torso_stack": 0.20,
                    "balance_control": 0.25,
                    "confidence": 0.25,
                },
                "balance_stability": {
                    "balance_control": 0.55,
                    "motion_stability": 0.25,
                    "confidence": 0.20,
                },
                "hip_stability": {
                    "hip_alignment": 0.45,
                    "balance_control": 0.25,
                    "motion_stability": 0.30,
                },
                "torso_alignment": {
                    "torso_stack": 0.55,
                    "movement_control": 0.25,
                    "balance_control": 0.20,
                },
                "repetition_consistency": {
                    "repeatability": 0.60,
                    "tempo": 0.20,
                    "payload_completeness": 0.20,
                },
            },
            metric_biases={
                "balance_stability": -0.12,
                "hip_stability": -0.10,
                "torso_alignment": -0.08,
                "repetition_consistency": -0.10,
            },
        )
