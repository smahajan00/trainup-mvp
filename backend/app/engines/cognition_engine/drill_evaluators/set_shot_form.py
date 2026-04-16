from __future__ import annotations

from app.engines.cognition_engine.drill_evaluators.base import BaseDrillEvaluator


class SetShotFormEvaluator(BaseDrillEvaluator):
    def __init__(self) -> None:
        super().__init__(
            evaluator_name="SetShotFormEvaluator",
            metric_weights={
                "shooting_alignment": {
                    "shooting_line": 0.55,
                    "elbow_track": 0.25,
                    "shoulder_stack": 0.20,
                },
                "elbow_angle_consistency": {
                    "elbow_track": 0.60,
                    "repeatability": 0.25,
                    "confidence": 0.15,
                },
                "shoulder_control": {
                    "shoulder_stack": 0.55,
                    "torso_stack": 0.25,
                    "motion_stability": 0.20,
                },
                "balance_stability": {
                    "balance_control": 0.60,
                    "motion_stability": 0.25,
                    "coverage": 0.15,
                },
                "posture_accuracy": {
                    "movement_control": 0.25,
                    "torso_stack": 0.30,
                    "balance_control": 0.20,
                    "shooting_line": 0.25,
                },
            },
            metric_biases={
                "shooting_alignment": -0.12,
                "elbow_angle_consistency": -0.10,
                "shoulder_control": -0.10,
                "posture_accuracy": -0.08,
            },
        )
