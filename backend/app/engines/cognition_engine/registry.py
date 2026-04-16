from __future__ import annotations

from app.engines.cognition_engine.drill_evaluators import (
    BasicShootingFormEvaluator,
    BaseDrillEvaluator,
    BodyweightSquatEvaluator,
    DefensiveStanceEvaluator,
    DumbbellShoulderPressEvaluator,
    InstepPassEvaluator,
    SetShotFormEvaluator,
)

_EVALUATOR_REGISTRY: dict[str, BaseDrillEvaluator] = {
    "Bodyweight Squat": BodyweightSquatEvaluator(),
    "Dumbbell Shoulder Press": DumbbellShoulderPressEvaluator(),
    "Instep Pass": InstepPassEvaluator(),
    "Basic Shooting Form": BasicShootingFormEvaluator(),
    "Set Shot Form": SetShotFormEvaluator(),
    "Defensive Stance": DefensiveStanceEvaluator(),
}


def get_evaluator_for_drill(drill_name: str) -> BaseDrillEvaluator:
    evaluator = _EVALUATOR_REGISTRY.get(drill_name)
    if evaluator is None:
        raise ValueError(f"No deterministic evaluator is registered for drill '{drill_name}'.")
    return evaluator
