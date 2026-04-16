from __future__ import annotations

from app.engines.cognition_engine.drill_evaluators.base import BaseDrillEvaluator


class DumbbellShoulderPressEvaluator(BaseDrillEvaluator):
    def __init__(self) -> None:
        super().__init__(
            evaluator_name="DumbbellShoulderPressEvaluator",
            metric_weights={
                "posture_accuracy": {
                    "movement_control": 0.25,
                    "torso_stack": 0.35,
                    "balance_control": 0.20,
                    "confidence": 0.20,
                },
                "elbow_angle_consistency": {
                    "elbow_track": 0.60,
                    "repeatability": 0.25,
                    "confidence": 0.15,
                },
                "shoulder_control": {
                    "shoulder_stack": 0.55,
                    "motion_stability": 0.25,
                    "movement_control": 0.20,
                },
                "torso_alignment": {
                    "torso_stack": 0.60,
                    "balance_control": 0.20,
                    "motion_stability": 0.20,
                },
                "balance_stability": {
                    "balance_control": 0.55,
                    "motion_stability": 0.25,
                    "payload_completeness": 0.20,
                },
            },
            metric_biases={
                "elbow_angle_consistency": -0.12,
                "shoulder_control": -0.11,
                "torso_alignment": -0.10,
                "balance_stability": -0.08,
            },
        )
