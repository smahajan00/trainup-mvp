from __future__ import annotations

from app.engines.cognition_engine.drill_evaluators.base import BaseDrillEvaluator


class DefensiveStanceEvaluator(BaseDrillEvaluator):
    def __init__(self) -> None:
        super().__init__(
            evaluator_name="DefensiveStanceEvaluator",
            metric_weights={
                "stance_width_control": {
                    "stance_width": 0.60,
                    "balance_control": 0.25,
                    "hip_alignment": 0.15,
                },
                "knee_alignment_score": {
                    "knee_track": 0.55,
                    "stance_width": 0.20,
                    "balance_control": 0.25,
                },
                "hip_stability": {
                    "hip_alignment": 0.50,
                    "balance_control": 0.25,
                    "motion_stability": 0.25,
                },
                "torso_alignment": {
                    "torso_stack": 0.60,
                    "balance_control": 0.20,
                    "movement_control": 0.20,
                },
                "balance_stability": {
                    "balance_control": 0.60,
                    "motion_stability": 0.25,
                    "stance_width": 0.15,
                },
            },
            metric_biases={
                "stance_width_control": -0.14,
                "knee_alignment_score": -0.10,
                "balance_stability": -0.10,
            },
        )
