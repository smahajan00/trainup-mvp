from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.engines.cognition_engine.evaluators import (
    build_evaluation_summary_flags,
    evaluate_rule_checks,
)
from app.engines.cognition_engine.metrics import compute_common_signals, score_metric
from app.models.drill import Drill
from app.models.training_session import TrainingSession
from app.schemas.session import DrillEvaluationResult, PerceptionResult


@dataclass
class BaseDrillEvaluator:
    evaluator_name: str
    metric_weights: dict[str, dict[str, float]] = field(default_factory=dict)
    metric_biases: dict[str, float] = field(default_factory=dict)

    def evaluate(
        self,
        *,
        perception_payload: PerceptionResult,
        drill: Drill,
        session: TrainingSession,
    ) -> DrillEvaluationResult:
        reference_payload = drill.reference_payload or {}
        coaching_rules = drill.coaching_rules or {}
        target_metrics = list((drill.target_metrics or {}).get("metrics", []))
        common_signals = compute_common_signals(perception_payload, reference_payload)

        metric_scores: dict[str, float] = {}
        for metric_name in target_metrics:
            metric_scores[metric_name] = score_metric(
                signal_values=common_signals,
                weights=self.metric_weights.get(metric_name, {"movement_control": 1.0}),
                bias=self.metric_biases.get(metric_name, 0.0),
            )

        issues = evaluate_rule_checks(
            metric_scores=metric_scores,
            coaching_rules=coaching_rules,
        )

        evaluation_result = DrillEvaluationResult(
            evaluation_mode="deterministic_scaffold",
            session_id=session.id,
            drill_id=drill.id,
            drill_name=drill.drill_name,
            evaluator_name=self.evaluator_name,
            metric_scores=metric_scores,
            issues=issues,
            summary_flags=[],
            feedback_count=len(issues),
        )
        evaluation_result.summary_flags = build_evaluation_summary_flags(
            evaluation_result=evaluation_result
        )
        return evaluation_result
