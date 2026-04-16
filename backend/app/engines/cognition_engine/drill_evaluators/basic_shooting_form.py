from __future__ import annotations

from app.engines.cognition_engine.drill_evaluators.base import BaseDrillEvaluator


class BasicShootingFormEvaluator(BaseDrillEvaluator):
    def __init__(self) -> None:
        super().__init__(
            evaluator_name="BasicShootingFormEvaluator",
            metric_weights={
                "posture_accuracy": {
                    "movement_control": 0.30,
                    "torso_stack": 0.25,
                    "balance_control": 0.20,
                    "confidence": 0.25,
                },
                "hip_stability": {
                    "hip_alignment": 0.45,
                    "balance_control": 0.25,
                    "motion_stability": 0.30,
                },
                "balance_stability": {
                    "balance_control": 0.55,
                    "motion_stability": 0.25,
                    "payload_completeness": 0.20,
                },
                "torso_alignment": {
                    "torso_stack": 0.60,
                    "movement_control": 0.20,
                    "balance_control": 0.20,
                },
                "knee_alignment_score": {
                    "knee_track": 0.50,
                    "balance_control": 0.25,
                    "hip_alignment": 0.15,
                    "coverage": 0.10,
                },
            },
            metric_biases={
                "hip_stability": -0.10,
                "balance_stability": -0.10,
                "knee_alignment_score": -0.09,
            },
        )
