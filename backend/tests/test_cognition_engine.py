from __future__ import annotations

from app.engines.cognition_engine.evaluators import classify_severity_level
from app.engines.cognition_engine.registry import get_evaluator_for_drill
from app.models.enums import SeverityLevel


def test_evaluator_selection_covers_all_seeded_drills() -> None:
    expected_evaluators = {
        "Bodyweight Squat": "BodyweightSquatEvaluator",
        "Dumbbell Shoulder Press": "DumbbellShoulderPressEvaluator",
        "Instep Pass": "InstepPassEvaluator",
        "Basic Shooting Form": "BasicShootingFormEvaluator",
        "Set Shot Form": "SetShotFormEvaluator",
        "Defensive Stance": "DefensiveStanceEvaluator",
    }

    for drill_name, evaluator_class in expected_evaluators.items():
        assert get_evaluator_for_drill(drill_name).__class__.__name__ == evaluator_class


def test_severity_classification_is_deterministic() -> None:
    thresholds = {"minor": 0.15, "moderate": 0.30, "severe": 0.45}

    assert (
        classify_severity_level(
            deviation=0.02,
            thresholds=thresholds,
            severity_weight=0.90,
        )
        == SeverityLevel.MINOR
    )
    assert (
        classify_severity_level(
            deviation=0.07,
            thresholds=thresholds,
            severity_weight=0.90,
        )
        == SeverityLevel.MODERATE
    )
    assert (
        classify_severity_level(
            deviation=0.11,
            thresholds=thresholds,
            severity_weight=0.95,
        )
        == SeverityLevel.SEVERE
    )
