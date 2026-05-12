from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from app.models.enums import SeverityLevel
from app.models.training_session import TrainingSession
from app.schemas.session import (
    ChoquetAggregationResult,
    DeterministicEvaluationResult,
    DeterministicFeedbackItemResponse,
    DeterministicFeedbackResult,
    FuzzyInterpretationResult,
    IT2FuzzyInterpretationResult,
    LLMEnhancedFeedbackItemResponse,
    LLMEnhancedSessionSummaryResponse,
    LLMFeedbackResult,
    LLM_FEEDBACK_VERSION,
    MetricEvaluationResultResponse,
    OntologyReasoningResult,
    PedagogicalDecisionResult,
    TemporalModelingResult,
)
from app.services.llm_client import (
    LLMClient,
    LLMClientError,
    LLMMessage,
    LLMProviderConfig,
    is_gemini_provider,
)


_UNSAFE_TERMS = ("pain", "injury", "diagnose", "diagnosis", "doctor", "medical")
_INTERNAL_ANALYSIS_TERMS = (
    "fuzzy",
    "choquet",
    "ontology",
    "it2",
    "it2 fuzzy",
    "temporal model",
    "diagnostic flag",
)
logger = logging.getLogger("uvicorn.error")
_JSON_FENCE_RE = re.compile(
    r"```(?:json)?\s*(?P<body>.*?)\s*```",
    re.IGNORECASE | re.DOTALL,
)
_MAIN_CUE_KEY = "main_coaching_cue"
_FIX_KEY = "what_to_fix"
_NEXT_SESSION_KEY = "next_session_cue"
_LABEL_TO_KEY = {
    "main cue": _MAIN_CUE_KEY,
    "fix": _FIX_KEY,
    "next session cue": _NEXT_SESSION_KEY,
}
_LABELED_LINE_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(main cue|fix|next session cue)\s*:\s*(.*)$",
    re.IGNORECASE,
)
_ISSUE_RESPONSE_REQUIRED_KEYS = frozenset(
    {
        "main_coaching_cue",
        "what_happened",
        "why_it_matters",
        "what_to_fix",
        "next_session_cue",
        "grounding_fields_used",
    }
)
_SUMMARY_RESPONSE_REQUIRED_KEYS = frozenset({"summary", "grounding_fields_used"})


@dataclass(frozen=True)
class CoachingIssueContext:
    session_id: str
    sport_id: str
    sport_name: str
    drill_id: str
    drill_name: str
    skill_level: str
    overall_score: float
    overall_severity: str
    phase_id: str
    metric_id: str | None
    metric_name: str
    severity_level: str
    priority_rank: int
    affected_body_part: str
    issue_direction: str
    raw_value: float | None
    unit: str | None
    ideal_min: float | None
    ideal_max: float | None
    deviation: float
    deterministic_coaching_cue: str
    deterministic_improvement_suggestion: str
    strongest_area: str | None
    weakest_area: str | None
    advanced_reasoning_context: dict[str, Any]
    diagnostic_flags: list[str]


@dataclass(frozen=True)
class CoachingSummaryContext:
    session_id: str
    sport_id: str
    sport_name: str
    drill_id: str
    drill_name: str
    skill_level: str
    overall_score: float
    overall_severity: str
    deterministic_summary: str
    top_issue: dict[str, Any] | None
    secondary_issues: list[dict[str, Any]]
    strongest_area: str | None
    weakest_area: str | None
    improvement_suggestions: list[str]
    advanced_reasoning_context: dict[str, Any]
    diagnostic_flags: list[str]


@dataclass(frozen=True)
class CoachingContext:
    issue_contexts: list[CoachingIssueContext]
    summary_context: CoachingSummaryContext
    advanced_context_used: bool
    advanced_context_sources: list[str]
    context_diagnostic_flags: list[str]


@dataclass(frozen=True)
class CoachingContextBuilder:
    def build(
        self,
        *,
        session: TrainingSession,
        evaluation_result: DeterministicEvaluationResult,
        feedback_result: DeterministicFeedbackResult,
        fuzzy_result: FuzzyInterpretationResult | None = None,
        it2_fuzzy_result: IT2FuzzyInterpretationResult | None = None,
        pedagogical_result: PedagogicalDecisionResult | None = None,
        ontology_result: OntologyReasoningResult | None = None,
        choquet_result: ChoquetAggregationResult | None = None,
        temporal_result: TemporalModelingResult | None = None,
        context_diagnostic_flags: list[str] | None = None,
    ) -> CoachingContext:
        metric_results = self._metric_results_by_key(evaluation_result)
        strongest_area = self._ranked_metric_label(evaluation_result.strongest_metrics[:1])
        weakest_area = self._ranked_metric_label(evaluation_result.weakest_metrics[:1])
        context_sources, advanced_context_flags = self._resolve_advanced_context_status(
            fuzzy_result=fuzzy_result,
            it2_fuzzy_result=it2_fuzzy_result,
            pedagogical_result=pedagogical_result,
            ontology_result=ontology_result,
            choquet_result=choquet_result,
            temporal_result=temporal_result,
            existing_flags=context_diagnostic_flags or [],
        )
        fuzzy_index = self._fuzzy_index(fuzzy_result)
        it2_index = self._it2_index(it2_fuzzy_result)
        pedagogy_index = self._pedagogy_index(pedagogical_result)
        ontology_metric_concepts = self._ontology_metric_concepts(ontology_result)
        ontology_metric_regions = self._ontology_metric_regions(ontology_result)
        choquet_groups = choquet_result.concept_aggregation if choquet_result is not None else {}
        temporal_phase_index = self._temporal_phase_index(temporal_result)
        issue_contexts = [
            self._build_issue_context(
                session=session,
                evaluation_result=evaluation_result,
                feedback_item=feedback_item,
                metric_result=metric_results.get(
                    (feedback_item.phase_id, feedback_item.metric_id or feedback_item.metric_name)
                ),
                strongest_area=strongest_area,
                weakest_area=weakest_area,
                fuzzy_metric=fuzzy_index.get(
                    (feedback_item.phase_id, feedback_item.metric_id or feedback_item.metric_name)
                ),
                it2_metric=it2_index.get(
                    (feedback_item.phase_id, feedback_item.metric_id or feedback_item.metric_name)
                ),
                pedagogical_focus=pedagogy_index.get(
                    (feedback_item.phase_id, feedback_item.metric_id or feedback_item.metric_name)
                ),
                ontology_result=ontology_result,
                metric_concepts=ontology_metric_concepts.get(
                    feedback_item.metric_id or feedback_item.metric_name,
                    set(),
                ),
                metric_region=ontology_metric_regions.get(
                    feedback_item.metric_id or feedback_item.metric_name
                ),
                choquet_groups=choquet_groups,
                temporal_phase=temporal_phase_index.get(feedback_item.phase_id),
                pedagogical_result=pedagogical_result,
                temporal_result=temporal_result,
            )
            for feedback_item in feedback_result.prioritized_feedback_items
        ]

        return CoachingContext(
            issue_contexts=issue_contexts,
            summary_context=self._build_summary_context(
                session=session,
                evaluation_result=evaluation_result,
                feedback_result=feedback_result,
                issue_contexts=issue_contexts,
                strongest_area=strongest_area,
                weakest_area=weakest_area,
                fuzzy_result=fuzzy_result,
                it2_fuzzy_result=it2_fuzzy_result,
                pedagogical_result=pedagogical_result,
                ontology_result=ontology_result,
                choquet_result=choquet_result,
                temporal_result=temporal_result,
                ontology_metric_regions=ontology_metric_regions,
            ),
            advanced_context_used=bool(context_sources),
            advanced_context_sources=context_sources,
            context_diagnostic_flags=self._dedupe(advanced_context_flags),
        )

    @staticmethod
    def _metric_results_by_key(
        evaluation_result: DeterministicEvaluationResult,
    ) -> dict[tuple[str, str], MetricEvaluationResultResponse]:
        indexed: dict[tuple[str, str], MetricEvaluationResultResponse] = {}
        for phase in evaluation_result.phase_results:
            for metric in phase.metric_results:
                metric_key = metric.metric_id or metric.metric_name
                indexed[(metric.phase_id, metric_key)] = metric
        return indexed

    def _build_issue_context(
        self,
        *,
        session: TrainingSession,
        evaluation_result: DeterministicEvaluationResult,
        feedback_item: DeterministicFeedbackItemResponse,
        metric_result: MetricEvaluationResultResponse | None,
        strongest_area: str | None,
        weakest_area: str | None,
        fuzzy_metric: Any | None,
        it2_metric: Any | None,
        pedagogical_focus: Any | None,
        ontology_result: OntologyReasoningResult | None,
        metric_concepts: set[str],
        metric_region: str | None,
        choquet_groups: dict[str, Any],
        temporal_phase: Any | None,
        pedagogical_result: PedagogicalDecisionResult | None,
        temporal_result: TemporalModelingResult | None,
    ) -> CoachingIssueContext:
        sport = session.drill.sport if session.drill is not None else None
        return CoachingIssueContext(
            session_id=str(evaluation_result.session_id),
            sport_id=str(evaluation_result.sport_id),
            sport_name=sport.sport_name if sport is not None else "",
            drill_id=str(evaluation_result.drill_id),
            drill_name=session.drill.drill_name,
            skill_level=evaluation_result.skill_level.value,
            overall_score=evaluation_result.overall_score,
            overall_severity=evaluation_result.overall_severity.value,
            phase_id=feedback_item.phase_id,
            metric_id=feedback_item.metric_id,
            metric_name=feedback_item.metric_name,
            severity_level=feedback_item.severity_level.value,
            priority_rank=feedback_item.priority_rank,
            affected_body_part=feedback_item.affected_body_part,
            issue_direction=feedback_item.issue_direction,
            raw_value=metric_result.raw_value if metric_result is not None else None,
            unit=metric_result.unit if metric_result is not None else None,
            ideal_min=metric_result.ideal_min if metric_result is not None else None,
            ideal_max=metric_result.ideal_max if metric_result is not None else None,
            deviation=feedback_item.deviation,
            deterministic_coaching_cue=feedback_item.coaching_cue,
            deterministic_improvement_suggestion=feedback_item.improvement_suggestion,
            strongest_area=strongest_area,
            weakest_area=weakest_area,
            advanced_reasoning_context=self._build_issue_advanced_context(
                fuzzy_metric=fuzzy_metric,
                it2_metric=it2_metric,
                pedagogical_focus=pedagogical_focus,
                pedagogical_result=pedagogical_result,
                ontology_result=ontology_result,
                metric_concepts=metric_concepts,
                metric_region=metric_region,
                choquet_groups=choquet_groups,
                temporal_phase=temporal_phase,
                temporal_result=temporal_result,
            ),
            diagnostic_flags=evaluation_result.diagnostic_flags,
        )

    def _build_summary_context(
        self,
        *,
        session: TrainingSession,
        evaluation_result: DeterministicEvaluationResult,
        feedback_result: DeterministicFeedbackResult,
        issue_contexts: list[CoachingIssueContext],
        strongest_area: str | None,
        weakest_area: str | None,
        fuzzy_result: FuzzyInterpretationResult | None,
        it2_fuzzy_result: IT2FuzzyInterpretationResult | None,
        pedagogical_result: PedagogicalDecisionResult | None,
        ontology_result: OntologyReasoningResult | None,
        choquet_result: ChoquetAggregationResult | None,
        temporal_result: TemporalModelingResult | None,
        ontology_metric_regions: dict[str, str],
    ) -> CoachingSummaryContext:
        sport = session.drill.sport if session.drill is not None else None
        top_issue = asdict(issue_contexts[0]) if issue_contexts else None
        secondary_issues = [asdict(issue) for issue in issue_contexts[1:3]]
        return CoachingSummaryContext(
            session_id=str(evaluation_result.session_id),
            sport_id=str(evaluation_result.sport_id),
            sport_name=sport.sport_name if sport is not None else "",
            drill_id=str(evaluation_result.drill_id),
            drill_name=session.drill.drill_name,
            skill_level=evaluation_result.skill_level.value,
            overall_score=evaluation_result.overall_score,
            overall_severity=evaluation_result.overall_severity.value,
            deterministic_summary=feedback_result.overall_feedback_summary,
            top_issue=top_issue,
            secondary_issues=secondary_issues,
            strongest_area=strongest_area,
            weakest_area=weakest_area,
            improvement_suggestions=feedback_result.improvement_suggestions,
            advanced_reasoning_context=self._build_summary_advanced_context(
                issue_contexts=issue_contexts,
                fuzzy_result=fuzzy_result,
                it2_fuzzy_result=it2_fuzzy_result,
                pedagogical_result=pedagogical_result,
                ontology_result=ontology_result,
                choquet_result=choquet_result,
                temporal_result=temporal_result,
                ontology_metric_regions=ontology_metric_regions,
            ),
            diagnostic_flags=(
                evaluation_result.diagnostic_flags + feedback_result.diagnostic_flags
            ),
        )

    @staticmethod
    def _ranked_metric_label(ranked_metrics) -> str | None:
        if not ranked_metrics:
            return None
        metric = ranked_metrics[0]
        return f"{metric.metric_name} in {metric.phase_id}"

    @staticmethod
    def _fuzzy_index(
        fuzzy_result: FuzzyInterpretationResult | None,
    ) -> dict[tuple[str, str], Any]:
        if fuzzy_result is None or fuzzy_result.status not in {
            "COMPLETED",
            "NO_INTERPRETABLE_METRICS",
        }:
            return {}
        return {
            (metric.phase_id, metric.metric_id or metric.metric_name): metric
            for metric in fuzzy_result.fuzzy_metric_results
        }

    @staticmethod
    def _it2_index(
        it2_fuzzy_result: IT2FuzzyInterpretationResult | None,
    ) -> dict[tuple[str, str], Any]:
        if it2_fuzzy_result is None or it2_fuzzy_result.status not in {
            "COMPLETED",
            "NO_INTERPRETABLE_METRICS",
            "DISABLED",
        }:
            return {}
        return {
            (metric.phase_id, metric.metric_id or metric.metric_name): metric
            for metric in it2_fuzzy_result.it2_metric_results
        }

    @staticmethod
    def _pedagogy_index(
        pedagogical_result: PedagogicalDecisionResult | None,
    ) -> dict[tuple[str, str], Any]:
        if pedagogical_result is None or pedagogical_result.status != "COMPLETED":
            return {}
        return {
            (item.phase_id, item.metric_id or item.metric_name): item
            for item in pedagogical_result.selected_focus_items
        }

    @staticmethod
    def _ontology_metric_concepts(
        ontology_result: OntologyReasoningResult | None,
    ) -> dict[str, set[str]]:
        if ontology_result is None or ontology_result.status not in {
            "COMPLETED",
            "NO_SIGNIFICANT_ISSUES",
        }:
            return {}
        concepts_by_metric: dict[str, set[str]] = {}
        for concept, group in ontology_result.concept_groups.items():
            for metric_id in group.metrics:
                concepts_by_metric.setdefault(metric_id, set()).add(concept)
        return concepts_by_metric

    @staticmethod
    def _ontology_metric_regions(
        ontology_result: OntologyReasoningResult | None,
    ) -> dict[str, str]:
        if ontology_result is None:
            return {}
        region_by_metric: dict[str, str] = {}
        for region, summary in ontology_result.body_region_summary.items():
            for metric_id in summary.metrics:
                region_by_metric.setdefault(metric_id, region)
        return region_by_metric

    @staticmethod
    def _temporal_phase_index(
        temporal_result: TemporalModelingResult | None,
    ) -> dict[str, Any]:
        if temporal_result is None or temporal_result.status not in {
            "COMPLETED",
            "INSUFFICIENT_DATA",
        }:
            return {}
        return {
            phase.phase_id: phase for phase in temporal_result.phase_temporal_results
        }

    def _resolve_advanced_context_status(
        self,
        *,
        fuzzy_result: FuzzyInterpretationResult | None,
        it2_fuzzy_result: IT2FuzzyInterpretationResult | None,
        pedagogical_result: PedagogicalDecisionResult | None,
        ontology_result: OntologyReasoningResult | None,
        choquet_result: ChoquetAggregationResult | None,
        temporal_result: TemporalModelingResult | None,
        existing_flags: list[str],
    ) -> tuple[list[str], list[str]]:
        sources: list[str] = []
        flags = list(existing_flags)
        artifact_status = [
            ("fuzzy_interpretation_result", fuzzy_result, {"COMPLETED", "NO_INTERPRETABLE_METRICS"}),
            ("it2_fuzzy_interpretation_result", it2_fuzzy_result, {"COMPLETED", "NO_INTERPRETABLE_METRICS", "DISABLED"}),
            ("pedagogical_decision_result", pedagogical_result, {"COMPLETED", "NO_ACTIONABLE_FEEDBACK"}),
            ("ontology_reasoning_result", ontology_result, {"COMPLETED", "NO_SIGNIFICANT_ISSUES"}),
            ("choquet_aggregation_result", choquet_result, {"COMPLETED", "NO_ACTIONABLE_ISSUES"}),
            ("temporal_modeling_result", temporal_result, {"COMPLETED", "INSUFFICIENT_DATA"}),
        ]
        for artifact_name, artifact, usable_statuses in artifact_status:
            if artifact is None:
                flags.append(f"ADVANCED_CONTEXT_MISSING:{artifact_name}")
                continue
            status_value = getattr(artifact, "status", None)
            if status_value in usable_statuses:
                sources.append(artifact_name)
            else:
                flags.append(f"ADVANCED_CONTEXT_UNUSABLE:{artifact_name}")
        return sources, flags

    def _build_issue_advanced_context(
        self,
        *,
        fuzzy_metric: Any | None,
        it2_metric: Any | None,
        pedagogical_focus: Any | None,
        pedagogical_result: PedagogicalDecisionResult | None,
        ontology_result: OntologyReasoningResult | None,
        metric_concepts: set[str],
        metric_region: str | None,
        choquet_groups: dict[str, Any],
        temporal_phase: Any | None,
        temporal_result: TemporalModelingResult | None,
    ) -> dict[str, Any]:
        context: dict[str, Any] = {}
        if fuzzy_metric is not None:
            context["fuzzy"] = {
                "top_metric_label": fuzzy_metric.primary_fuzzy_label,
                "direction_aware_label": fuzzy_metric.direction_aware_label,
                "dominant_label_confidence": fuzzy_metric.dominant_label_confidence,
            }
        if it2_metric is not None:
            context["it2_uncertainty"] = {
                "uncertainty_category": it2_metric.uncertainty_category,
                "uncertainty_width": it2_metric.uncertainty_width,
                "confidence_guidance": self._confidence_guidance(
                    getattr(it2_metric, "uncertainty_category", None)
                ),
            }
        if pedagogical_result is not None:
            pedagogy_context = {
                "teaching_strategy": pedagogical_result.teaching_strategy,
                "tone_profile": pedagogical_result.tone_profile,
                "correction_intensity": pedagogical_result.correction_intensity,
                "learning_objective": pedagogical_result.learning_objective,
                "progression_advice": pedagogical_result.progression_advice,
            }
            if pedagogical_focus is not None:
                pedagogy_context.update(
                    {
                        "selected_focus": True,
                        "teaching_reason": pedagogical_focus.teaching_reason,
                        "recommended_message_style": pedagogical_focus.recommended_message_style,
                    }
                )
            context["pedagogy"] = pedagogy_context
        if ontology_result is not None and ontology_result.status in {
            "COMPLETED",
            "NO_SIGNIFICANT_ISSUES",
        } and metric_concepts:
            context["ontology"] = {
                "concepts": sorted(metric_concepts),
                "primary_concept": ontology_result.primary_concept,
                "primary_body_region": metric_region,
                "reasoning_summary": ontology_result.reasoning_summary,
            }
        choquet_context = self._build_issue_choquet_context(
            metric_concepts=metric_concepts,
            choquet_groups=choquet_groups,
        )
        if choquet_context is not None:
            context["choquet"] = choquet_context
        if temporal_result is not None and temporal_phase is not None:
            context["temporal"] = {
                "overall_temporal_state": temporal_result.overall_temporal_state,
                "top_phase_temporal_state": temporal_phase.temporal_state,
                "temporal_summary": temporal_result.temporal_summary,
            }
        return context

    def _build_summary_advanced_context(
        self,
        *,
        issue_contexts: list[CoachingIssueContext],
        fuzzy_result: FuzzyInterpretationResult | None,
        it2_fuzzy_result: IT2FuzzyInterpretationResult | None,
        pedagogical_result: PedagogicalDecisionResult | None,
        ontology_result: OntologyReasoningResult | None,
        choquet_result: ChoquetAggregationResult | None,
        temporal_result: TemporalModelingResult | None,
        ontology_metric_regions: dict[str, str],
    ) -> dict[str, Any]:
        context: dict[str, Any] = {}
        if issue_contexts:
            top_issue_advanced = issue_contexts[0].advanced_reasoning_context
            if "fuzzy" in top_issue_advanced:
                context["fuzzy"] = top_issue_advanced["fuzzy"]
        if it2_fuzzy_result is not None and it2_fuzzy_result.status in {
            "COMPLETED",
            "NO_INTERPRETABLE_METRICS",
            "DISABLED",
        }:
            highest_uncertainty = it2_fuzzy_result.uncertainty_summary.highest_uncertainty_metric
            context["it2_uncertainty"] = {
                "low_count": it2_fuzzy_result.uncertainty_summary.low_count,
                "medium_count": it2_fuzzy_result.uncertainty_summary.medium_count,
                "high_count": it2_fuzzy_result.uncertainty_summary.high_count,
                "not_interpretable_count": it2_fuzzy_result.uncertainty_summary.not_interpretable_count,
                "average_uncertainty_width": it2_fuzzy_result.uncertainty_summary.average_uncertainty_width,
                "highest_uncertainty_metric": {
                    "phase_id": highest_uncertainty.phase_id,
                    "metric_id": highest_uncertainty.metric_id,
                    "uncertainty_width": highest_uncertainty.uncertainty_width,
                },
                "confidence_guidance": self._confidence_guidance_from_width(
                    it2_fuzzy_result.uncertainty_summary.average_uncertainty_width
                ),
            }
        if pedagogical_result is not None:
            context["pedagogy"] = {
                "teaching_strategy": pedagogical_result.teaching_strategy,
                "tone_profile": pedagogical_result.tone_profile,
                "correction_intensity": pedagogical_result.correction_intensity,
                "learning_objective": pedagogical_result.learning_objective,
                "progression_advice": pedagogical_result.progression_advice,
            }
        if ontology_result is not None and ontology_result.status in {
            "COMPLETED",
            "NO_SIGNIFICANT_ISSUES",
        }:
            context["ontology"] = {
                "primary_concept": ontology_result.primary_concept,
                "secondary_concepts": ontology_result.secondary_concepts[:3],
                "primary_body_region": self._primary_body_region_from_summary(
                    ontology_result=ontology_result,
                    ontology_metric_regions=ontology_metric_regions,
                ),
                "reasoning_summary": ontology_result.reasoning_summary,
            }
        if choquet_result is not None and choquet_result.status in {
            "COMPLETED",
            "NO_ACTIONABLE_ISSUES",
        }:
            interaction_summary = None
            if choquet_result.dominant_interaction_group is not None:
                dominant_group = choquet_result.concept_aggregation.get(
                    choquet_result.dominant_interaction_group
                )
                interaction_summary = (
                    dominant_group.explanation if dominant_group is not None else None
                )
            context["choquet"] = {
                "dominant_interaction_group": choquet_result.dominant_interaction_group,
                "overall_choquet_score": choquet_result.overall_choquet_score,
                "interaction_summary": interaction_summary,
            }
        if temporal_result is not None and temporal_result.status in {
            "COMPLETED",
            "INSUFFICIENT_DATA",
        }:
            top_phase = self._top_temporal_phase(temporal_result)
            context["temporal"] = {
                "overall_temporal_state": temporal_result.overall_temporal_state,
                "top_phase_temporal_state": (
                    None if top_phase is None else top_phase.temporal_state
                ),
                "temporal_summary": temporal_result.temporal_summary,
            }
        return context

    @staticmethod
    def _build_issue_choquet_context(
        *,
        metric_concepts: set[str],
        choquet_groups: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not metric_concepts or not choquet_groups:
            return None
        candidates = [
            (group_name, group)
            for group_name, group in choquet_groups.items()
            if set(group.concepts) & metric_concepts
        ]
        if not candidates:
            return None
        group_name, group = max(
            candidates,
            key=lambda item: (item[1].choquet_score, item[0]),
        )
        return {
            "dominant_interaction_group": group_name,
            "overall_choquet_score": group.choquet_score,
            "interaction_summary": group.explanation,
        }

    @staticmethod
    def _confidence_guidance(uncertainty_category: str | None) -> str | None:
        if uncertainty_category == "LOW_UNCERTAINTY":
            return "high_certainty"
        if uncertainty_category == "MEDIUM_UNCERTAINTY":
            return "moderate_certainty"
        if uncertainty_category == "HIGH_UNCERTAINTY":
            return "low_certainty"
        return None

    @staticmethod
    def _confidence_guidance_from_width(average_width: float) -> str:
        if average_width <= 0.12:
            return "high_certainty"
        if average_width <= 0.22:
            return "moderate_certainty"
        return "low_certainty"

    @staticmethod
    def _primary_body_region_from_summary(
        *,
        ontology_result: OntologyReasoningResult,
        ontology_metric_regions: dict[str, str],
    ) -> str | None:
        if ontology_result.primary_concept is not None:
            concept_group = ontology_result.concept_groups.get(ontology_result.primary_concept)
            if concept_group is not None:
                for metric_id in concept_group.metrics:
                    region = ontology_metric_regions.get(metric_id)
                    if region is not None:
                        return region
        ranked_regions = [
            (region, summary.total_weight)
            for region, summary in ontology_result.body_region_summary.items()
        ]
        if not ranked_regions:
            return None
        return max(ranked_regions, key=lambda item: (item[1], item[0]))[0]

    @staticmethod
    def _top_temporal_phase(temporal_result: TemporalModelingResult | None) -> Any | None:
        if temporal_result is None or not temporal_result.phase_temporal_results:
            return None
        return max(
            temporal_result.phase_temporal_results,
            key=lambda phase: (
                _ADVANCED_TEMPORAL_STATE_PRIORITY.get(phase.temporal_state, -1),
                phase.state_confidence,
                phase.phase_id,
            ),
        )

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        deduped: list[str] = []
        for value in values:
            if value not in deduped:
                deduped.append(value)
        return deduped


_ADVANCED_TEMPORAL_STATE_PRIORITY = {
    "INCOMPLETE": 5,
    "UNCERTAIN": 4,
    "JERKY": 3,
    "RUSHED": 2,
    "CONTROLLED": 1,
    "STABLE": 0,
}


@dataclass(frozen=True)
class LLMFeedbackPromptBuilder:
    def build_issue_prompt(self, context: CoachingIssueContext) -> list[LLMMessage]:
        context_payload = self._compact_issue_context(context)
        return [
            LLMMessage(role="system", content=self._system_instruction()),
            LLMMessage(
                role="user",
                content=(
                    "Rewrite this deterministic coaching item for the athlete.\n"
                    "Use only the JSON context. Return three short lines in plain text using this exact format:\n"
                    "Main cue: <one short sentence>\n"
                    "Fix: <one short sentence>\n"
                    "Next session cue: <one short sentence>\n"
                    "Do not return JSON. Do not include markdown, code fences, or explanation. "
                    "Do not prefix the response with phrases like Here is the JSON requested.\n"
                    "Use deterministic evaluation as the source of truth. "
                    "Do not add issues, body regions, metrics, causes, or priorities that are not present in context. "
                    "Use advanced reasoning only to refine wording, explanation, prioritization, and coaching clarity. "
                    "Fuzzy context: use linguistic movement severity to explain what the issue feels like. "
                    "Uncertainty context: if confidence guidance is low_certainty, soften wording with appears to, may be, or try checking; if high_certainty, speak more directly. "
                    "Pedagogy context: match cue complexity to skill level; beginner means one simple correction, advanced can be more precise. "
                    "Movement concept context: explain related body concepts naturally, such as lower-body control, without method names. "
                    "Linked-issue context: if related issues appeared together, explain the connection simply. "
                    "Timing context: if state is RUSHED, JERKY, CONTROLLED, or STABLE, add a pacing or control cue. "
                    "Do not mention internal terms like ontology, Choquet, IT2 fuzzy, temporal model, or diagnostic flags.\n"
                    f"Context:\n{json.dumps(context_payload, sort_keys=True)}"
                ),
            ),
        ]

    def build_summary_prompt(self, context: CoachingSummaryContext) -> list[LLMMessage]:
        context_payload = self._compact_summary_context(context)
        return [
            LLMMessage(role="system", content=self._system_instruction()),
            LLMMessage(
                role="user",
                content=(
                    "Create a concise session summary for the athlete.\n"
                    "Use only the JSON context. Mention the highest-priority issue first, "
                    "optionally mention one strength, and give one next-step action.\n"
                    "Return plain text only, no more than three short sentences. "
                    "Do not return JSON. Do not include markdown, code fences, or explanation. "
                    "Do not prefix the response with phrases like Here is the JSON requested.\n"
                    "Use deterministic evaluation as the source of truth. "
                    "Do not add issues, body regions, metrics, causes, or priorities that are not present in context. "
                    "Use advanced reasoning only to refine wording, explanation, prioritization, and coaching clarity. "
                    "Fuzzy context: use linguistic movement severity to explain what the issue feels like. "
                    "Uncertainty context: if confidence guidance is low_certainty, soften wording with appears to, may be, or try checking; if high_certainty, speak more directly. "
                    "Pedagogy context: match cue complexity to skill level; beginner means one simple correction, advanced can be more precise. "
                    "Movement concept context: explain related body concepts naturally, such as lower-body control, without method names. "
                    "Linked-issue context: if related issues appeared together, explain the connection simply. "
                    "Timing context: if state is RUSHED, JERKY, CONTROLLED, or STABLE, add a pacing or control cue. "
                    "Do not mention internal terms like ontology, Choquet, IT2 fuzzy, temporal model, or diagnostic flags.\n"
                    f"Context:\n{json.dumps(context_payload, sort_keys=True)}"
                ),
            ),
        ]

    @staticmethod
    def _compact_issue_context(context: CoachingIssueContext) -> dict[str, Any]:
        return {
            "drill": {
                "sport": context.sport_name,
                "name": context.drill_name,
                "skill_level": context.skill_level,
            },
            "evaluation": {
                "overall_score": context.overall_score,
                "overall_severity": context.overall_severity,
                "strongest_area": context.strongest_area,
                "weakest_area": context.weakest_area,
            },
            "deterministic_feedback": {
                "priority_rank": context.priority_rank,
                "phase": context.phase_id,
                "metric": context.metric_name,
                "severity": context.severity_level,
                "affected_body_part": context.affected_body_part,
                "issue_direction": context.issue_direction,
                "coaching_cue": context.deterministic_coaching_cue,
                "improvement_suggestion": context.deterministic_improvement_suggestion,
            },
            "advanced_reasoning_summaries": context.advanced_reasoning_context,
        }

    @classmethod
    def _compact_summary_context(cls, context: CoachingSummaryContext) -> dict[str, Any]:
        return {
            "drill": {
                "sport": context.sport_name,
                "name": context.drill_name,
                "skill_level": context.skill_level,
            },
            "evaluation": {
                "overall_score": context.overall_score,
                "overall_severity": context.overall_severity,
                "strongest_area": context.strongest_area,
                "weakest_area": context.weakest_area,
            },
            "deterministic_feedback": {
                "summary": context.deterministic_summary,
                "improvement_suggestions": context.improvement_suggestions[:3],
            },
            "top_issue": cls._compact_issue_dict(context.top_issue),
            "secondary_issues": [
                cls._compact_issue_dict(issue)
                for issue in context.secondary_issues[:2]
                if issue is not None
            ],
            "advanced_reasoning_summaries": context.advanced_reasoning_context,
        }

    @staticmethod
    def _compact_issue_dict(issue: dict[str, Any] | None) -> dict[str, Any] | None:
        if not issue:
            return None
        return {
            "priority_rank": issue.get("priority_rank"),
            "phase": issue.get("phase_id"),
            "metric": issue.get("metric_name"),
            "severity": issue.get("severity_level"),
            "affected_body_part": issue.get("affected_body_part"),
            "issue_direction": issue.get("issue_direction"),
            "coaching_cue": issue.get("deterministic_coaching_cue"),
            "improvement_suggestion": issue.get("deterministic_improvement_suggestion"),
            "advanced_reasoning_summaries": issue.get("advanced_reasoning_context", {}),
        }

    @staticmethod
    def _system_instruction() -> str:
        return (
            "You are a controlled sports coaching communication layer. "
            "The deterministic evaluator is the source of truth. "
            "Only explain the supplied findings. Do not invent new faults, metrics, "
            "diagnoses, pain, injury claims, or unsupported body mechanics. "
            "Do not contradict severity or priority ordering. "
            "Use advanced reasoning only to explain emphasis, delivery, prioritization, and clarity, never to invent diagnosis. "
            "Adapt wording to the drill, phase, and skill level. "
            "Use movement severity labels to describe how the issue feels. "
            "If uncertainty is high, use softer wording; if uncertainty is low, speak more directly. "
            "Match wording complexity to the teaching strategy and athlete skill level. "
            "Use movement concepts and body regions in natural coaching language. "
            "If related issues appeared together, explain that they showed up together. "
            "If timing is rushed, jerky, controlled, or stable, include a pacing cue. "
            "Do not mention internal analysis terms such as ontology, Choquet, IT2 fuzzy, temporal model, or diagnostic flags. "
            "Keep language short, safe, and coaching-oriented."
        )


@dataclass(frozen=True)
class LLMFeedbackService:
    llm_client: LLMClient
    provider_config: LLMProviderConfig
    context_builder: CoachingContextBuilder
    prompt_builder: LLMFeedbackPromptBuilder

    def enhance(
        self,
        *,
        session: TrainingSession,
        evaluation_result: DeterministicEvaluationResult,
        feedback_result: DeterministicFeedbackResult,
        fuzzy_result: FuzzyInterpretationResult | None = None,
        it2_fuzzy_result: IT2FuzzyInterpretationResult | None = None,
        pedagogical_result: PedagogicalDecisionResult | None = None,
        ontology_result: OntologyReasoningResult | None = None,
        choquet_result: ChoquetAggregationResult | None = None,
        temporal_result: TemporalModelingResult | None = None,
        context_diagnostic_flags: list[str] | None = None,
    ) -> LLMFeedbackResult:
        context = self.context_builder.build(
            session=session,
            evaluation_result=evaluation_result,
            feedback_result=feedback_result,
            fuzzy_result=fuzzy_result,
            it2_fuzzy_result=it2_fuzzy_result,
            pedagogical_result=pedagogical_result,
            ontology_result=ontology_result,
            choquet_result=choquet_result,
            temporal_result=temporal_result,
            context_diagnostic_flags=context_diagnostic_flags,
        )
        diagnostic_flags = list(feedback_result.diagnostic_flags)
        configuration_flag = self._configuration_fallback_flag()

        enhanced_items: list[LLMEnhancedFeedbackItemResponse] = []
        for issue_context, feedback_item in zip(
            context.issue_contexts,
            feedback_result.prioritized_feedback_items,
            strict=True,
        ):
            if configuration_flag is not None:
                logger.info(
                    "LLM feedback using deterministic item fallback "
                    "session_id=%s provider=%s configured_model=%s reason=%s "
                    "deterministic_fallback_used=true",
                    str(evaluation_result.session_id),
                    self.provider_config.provider,
                    self.provider_config.model,
                    configuration_flag,
                )
                diagnostic_flags.append(configuration_flag)
                enhanced_items.append(self._fallback_item(feedback_item))
                continue

            enhanced_items.append(
                self._enhance_item(
                    issue_context=issue_context,
                    feedback_item=feedback_item,
                    diagnostic_flags=diagnostic_flags,
                )
            )

        enhanced_summary = self._enhance_summary(
            summary_context=context.summary_context,
            feedback_result=feedback_result,
            configuration_flag=configuration_flag,
            diagnostic_flags=diagnostic_flags,
        )

        fallback_used = configuration_flag is not None or (
            enhanced_summary.fallback_used
            and all(item.fallback_used for item in enhanced_items)
        )
        return LLMFeedbackResult(
            llm_feedback_version=LLM_FEEDBACK_VERSION,
            status="COMPLETED",
            session_id=evaluation_result.session_id,
            provider=self.provider_config.provider,
            model=self.provider_config.model,
            fallback_used=fallback_used,
            advanced_context_used=context.advanced_context_used,
            advanced_context_sources=context.advanced_context_sources,
            context_diagnostic_flags=context.context_diagnostic_flags,
            enhanced_feedback_items=enhanced_items,
            enhanced_summary=enhanced_summary,
            diagnostic_flags=self._dedupe(diagnostic_flags),
            created_at=datetime.now(UTC),
        )

    def _enhance_item(
        self,
        *,
        issue_context: CoachingIssueContext,
        feedback_item: DeterministicFeedbackItemResponse,
        diagnostic_flags: list[str],
    ) -> LLMEnhancedFeedbackItemResponse:
        try:
            raw_text = self._call_text(
                messages=self.prompt_builder.build_issue_prompt(issue_context)
            )
            main_coaching_cue, what_to_fix, next_session_cue = self._parse_issue_refinement_text(
                raw_text=raw_text,
                feedback_item=feedback_item,
            )
        except Exception as exc:
            logger.warning(
                "LLM item refinement failed; using deterministic fallback "
                "session_id=%s provider=%s configured_model=%s metric=%s "
                "exception_class=%s reason=%s deterministic_fallback_used=true",
                issue_context.session_id,
                self.provider_config.provider,
                self.provider_config.model,
                feedback_item.metric_id or feedback_item.metric_name,
                exc.__class__.__name__,
                str(exc),
            )
            diagnostic_flags.append(
                f"LLM_ITEM_FALLBACK:{feedback_item.metric_id or feedback_item.metric_name}"
            )
            return self._fallback_item(feedback_item)

        logger.info(
            "LLM item refinement succeeded session_id=%s provider=%s "
            "configured_model=%s metric=%s",
            issue_context.session_id,
            self.provider_config.provider,
            self.provider_config.model,
            feedback_item.metric_id or feedback_item.metric_name,
        )
        return LLMEnhancedFeedbackItemResponse(
            phase_id=feedback_item.phase_id,
            metric_id=feedback_item.metric_id,
            metric_name=feedback_item.metric_name,
            severity_level=feedback_item.severity_level,
            priority_rank=feedback_item.priority_rank,
            affected_body_part=feedback_item.affected_body_part,
            issue_direction=feedback_item.issue_direction,
            deterministic_coaching_cue=feedback_item.coaching_cue,
            llm_coaching_cue=main_coaching_cue,
            llm_main_coaching_cue=main_coaching_cue,
            llm_what_happened=feedback_item.what_happened,
            llm_why_it_matters=feedback_item.why_it_matters,
            llm_what_to_fix=what_to_fix,
            llm_next_session_cue=next_session_cue,
            deterministic_improvement_suggestion=feedback_item.improvement_suggestion,
            llm_improvement_suggestion=next_session_cue,
            grounding_fields_used=[
                "deterministic_coaching_cue",
                "deterministic_improvement_suggestion",
                "advanced_reasoning_summaries",
            ],
            fallback_used=False,
        )

    def _enhance_summary(
        self,
        *,
        summary_context: CoachingSummaryContext,
        feedback_result: DeterministicFeedbackResult,
        configuration_flag: str | None,
        diagnostic_flags: list[str],
    ) -> LLMEnhancedSessionSummaryResponse:
        if configuration_flag is not None:
            logger.info(
                "LLM feedback using deterministic summary fallback "
                "session_id=%s provider=%s configured_model=%s reason=%s "
                "deterministic_fallback_used=true",
                summary_context.session_id,
                self.provider_config.provider,
                self.provider_config.model,
                configuration_flag,
            )
            diagnostic_flags.append(configuration_flag)
            return self._fallback_summary(feedback_result)

        try:
            raw_text = self._call_text(
                messages=self.prompt_builder.build_summary_prompt(summary_context)
            )
            summary = self._parse_summary_refinement_text(raw_text)
        except Exception as exc:
            logger.warning(
                "LLM summary refinement failed; using deterministic fallback "
                "session_id=%s provider=%s configured_model=%s exception_class=%s "
                "reason=%s deterministic_fallback_used=true",
                summary_context.session_id,
                self.provider_config.provider,
                self.provider_config.model,
                exc.__class__.__name__,
                str(exc),
            )
            diagnostic_flags.append("LLM_SUMMARY_FALLBACK")
            return self._fallback_summary(feedback_result)

        logger.info(
            "LLM summary refinement succeeded session_id=%s provider=%s "
            "configured_model=%s",
            summary_context.session_id,
            self.provider_config.provider,
            self.provider_config.model,
        )
        return LLMEnhancedSessionSummaryResponse(
            deterministic_summary=feedback_result.overall_feedback_summary,
            llm_summary=summary,
            grounding_fields_used=[
                "deterministic_summary",
                "top_issue",
                "advanced_reasoning_summaries",
            ],
            fallback_used=False,
        )

    def _call_text(self, *, messages: list[LLMMessage]) -> str:
        raw_response = self.llm_client.generate_text(
            messages=messages,
            config=self.provider_config,
        )
        if not isinstance(raw_response, str):
            raise LLMClientError("LLM response must be text.")
        normalized = self._normalize_llm_response_text(raw_response)
        if not normalized:
            raise LLMClientError("LLM response text was empty.")
        return normalized

    def _parse_issue_refinement_text(
        self,
        *,
        raw_text: str,
        feedback_item: DeterministicFeedbackItemResponse,
    ) -> tuple[str, str, str]:
        labels = self._extract_labeled_lines(raw_text)
        if labels:
            main_coaching_cue = self._validated_text(
                labels.get(_MAIN_CUE_KEY) or feedback_item.coaching_cue,
                max_length=240,
            )
            what_to_fix = self._validated_text(
                labels.get(_FIX_KEY)
                or feedback_item.what_to_fix
                or feedback_item.coaching_cue,
                max_length=240,
            )
            next_session_cue = self._validated_text(
                labels.get(_NEXT_SESSION_KEY)
                or feedback_item.next_rep_cue
                or feedback_item.improvement_suggestion,
                max_length=240,
            )
            return main_coaching_cue, what_to_fix, next_session_cue

        main_coaching_cue = self._validated_text(raw_text, max_length=240)
        what_to_fix = self._validated_text(
            feedback_item.what_to_fix or feedback_item.coaching_cue,
            max_length=240,
        )
        next_session_cue = self._validated_text(
            feedback_item.next_rep_cue or feedback_item.improvement_suggestion,
            max_length=240,
        )
        return main_coaching_cue, what_to_fix, next_session_cue

    def _parse_summary_refinement_text(self, raw_text: str) -> str:
        labels = self._extract_labeled_lines(raw_text)
        if labels:
            ordered = [
                labels[key]
                for key in (_MAIN_CUE_KEY, _FIX_KEY, _NEXT_SESSION_KEY)
                if labels.get(key)
            ]
            if ordered:
                return self._validated_text(" ".join(ordered), max_length=700)
        return self._validated_text(raw_text, max_length=700)

    def _call_json(
        self,
        *,
        messages: list[LLMMessage],
        required_keys: frozenset[str] | None = None,
    ) -> dict[str, Any]:
        started_at = time.perf_counter()
        raw_response = self.llm_client.generate_text(
            messages=messages,
            config=self.provider_config,
        )
        try:
            parsed = self.extract_json_object(raw_response)
        except json.JSONDecodeError as exc:
            logger.warning(
                "LLM JSON parse failed provider=%s configured_model=%s "
                "exception_class=%s parse_error=%s position=%s "
                "response_preview=%s "
                "deterministic_fallback_pending=true",
                self.provider_config.provider,
                self.provider_config.model,
                exc.__class__.__name__,
                exc.msg,
                exc.pos,
                self._safe_response_preview(raw_response),
            )
            raise LLMClientError(
                f"LLM response was not valid JSON ({exc.msg} at position {exc.pos})."
            ) from exc
        if not isinstance(parsed, dict):
            raise LLMClientError("LLM response JSON must be an object.")
        if required_keys is not None:
            missing_keys = sorted(required_keys - set(parsed))
            if missing_keys:
                logger.warning(
                    "LLM JSON validation failed provider=%s configured_model=%s "
                    "missing_keys=%s response_keys=%s response_preview=%s "
                    "deterministic_fallback_pending=true",
                    self.provider_config.provider,
                    self.provider_config.model,
                    missing_keys,
                    sorted(str(key) for key in parsed.keys())[:20],
                    self._safe_response_preview(raw_response),
                )
                raise LLMClientError(
                    f"LLM response missing required keys: {', '.join(missing_keys)}."
                )
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        logger.info(
            "Gemini refinement succeeded provider=%s configured_model=%s "
            "duration_ms=%s output_parse_success=true",
            self.provider_config.provider,
            self.provider_config.model,
            duration_ms,
        )
        logger.info(
            "LLM JSON extraction succeeded provider=%s configured_model=%s",
            self.provider_config.provider,
            self.provider_config.model,
        )
        return parsed

    @classmethod
    def extract_json_object(cls, raw_response: str) -> dict[str, Any]:
        text = raw_response.strip()
        if not text:
            raise json.JSONDecodeError("Empty LLM response", raw_response, 0)

        candidates = [text]
        candidates.extend(match.group("body").strip() for match in _JSON_FENCE_RE.finditer(text))

        last_error: json.JSONDecodeError | None = None
        for candidate in candidates:
            parsed, parse_error = cls._extract_first_balanced_json_object(candidate)
            if parsed is not None:
                return parsed
            if parse_error is not None:
                last_error = parse_error

        if last_error is not None:
            raise last_error
        position = max(text.find("{"), 0)
        raise json.JSONDecodeError("No JSON object found in LLM response", text, position)

    @staticmethod
    def _extract_first_balanced_json_object(
        text: str,
    ) -> tuple[dict[str, Any] | None, json.JSONDecodeError | None]:
        search_index = 0
        last_error: json.JSONDecodeError | None = None

        while True:
            start = text.find("{", search_index)
            if start < 0:
                return None, last_error

            depth = 0
            in_string = False
            escaped = False
            for index in range(start, len(text)):
                char = text[index]
                if in_string:
                    if escaped:
                        escaped = False
                    elif char == "\\":
                        escaped = True
                    elif char == '"':
                        in_string = False
                    continue

                if char == '"':
                    in_string = True
                    continue
                if char == "{":
                    depth += 1
                    continue
                if char == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = text[start : index + 1]
                        try:
                            parsed = json.loads(candidate)
                        except json.JSONDecodeError as exc:
                            last_error = exc
                            break
                        if not isinstance(parsed, dict):
                            last_error = json.JSONDecodeError(
                                "LLM response JSON must be an object",
                                candidate,
                                0,
                            )
                            break
                        return parsed, None

            search_index = start + 1

    @staticmethod
    def _safe_response_preview(raw_response: str, *, limit: int = 300) -> str:
        preview = re.sub(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
            "[uuid]",
            raw_response,
        )
        preview = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email]", preview)
        preview = " ".join(preview.split())
        return preview[:limit]

    @staticmethod
    def _normalize_llm_response_text(raw_response: str) -> str:
        text = raw_response.strip()
        fenced = _JSON_FENCE_RE.search(text)
        if fenced is not None:
            text = fenced.group("body").strip()
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.rstrip() for line in text.split("\n")]
        return "\n".join(line for line in lines if line.strip())

    @classmethod
    def _extract_labeled_lines(cls, raw_text: str) -> dict[str, str]:
        extracted: dict[str, list[str]] = {}
        current_key: str | None = None
        for raw_line in raw_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            match = _LABELED_LINE_RE.match(line)
            if match is not None:
                current_key = _LABEL_TO_KEY[match.group(1).lower()]
                value = match.group(2).strip()
                if value:
                    extracted.setdefault(current_key, []).append(value)
                continue
            if current_key is not None:
                extracted.setdefault(current_key, []).append(line.lstrip("-* ").strip())
        return {
            key: " ".join(part for part in parts if part).strip()
            for key, parts in extracted.items()
            if any(part.strip() for part in parts)
        }

    def _configuration_fallback_flag(self) -> str | None:
        if not self.provider_config.enhancement_enabled:
            return "LLM_ENHANCEMENT_DISABLED"
        if not self.provider_config.provider:
            return "LLM_PROVIDER_NOT_CONFIGURED"
        if not is_gemini_provider(self.provider_config.provider):
            return "LLM_PROVIDER_UNSUPPORTED"
        if not self.provider_config.model:
            return "LLM_MODEL_NOT_CONFIGURED"
        if not self.provider_config.api_key:
            return "LLM_API_KEY_MISSING"
        return None

    @staticmethod
    def _fallback_item(
        feedback_item: DeterministicFeedbackItemResponse,
    ) -> LLMEnhancedFeedbackItemResponse:
        return LLMEnhancedFeedbackItemResponse(
            phase_id=feedback_item.phase_id,
            metric_id=feedback_item.metric_id,
            metric_name=feedback_item.metric_name,
            severity_level=feedback_item.severity_level,
            priority_rank=feedback_item.priority_rank,
            affected_body_part=feedback_item.affected_body_part,
            issue_direction=feedback_item.issue_direction,
            deterministic_coaching_cue=feedback_item.coaching_cue,
            llm_coaching_cue=feedback_item.coaching_cue,
            llm_main_coaching_cue=feedback_item.coaching_cue,
            llm_what_happened=feedback_item.what_happened,
            llm_why_it_matters=feedback_item.why_it_matters,
            llm_what_to_fix=feedback_item.what_to_fix,
            llm_next_session_cue=feedback_item.next_rep_cue,
            deterministic_improvement_suggestion=feedback_item.improvement_suggestion,
            llm_improvement_suggestion=feedback_item.improvement_suggestion,
            grounding_fields_used=[
                "deterministic_coaching_cue",
                "deterministic_improvement_suggestion",
            ],
            fallback_used=True,
        )

    @staticmethod
    def _fallback_summary(
        feedback_result: DeterministicFeedbackResult,
    ) -> LLMEnhancedSessionSummaryResponse:
        return LLMEnhancedSessionSummaryResponse(
            deterministic_summary=feedback_result.overall_feedback_summary,
            llm_summary=feedback_result.overall_feedback_summary,
            grounding_fields_used=["deterministic_summary"],
            fallback_used=True,
        )

    @staticmethod
    def _validated_text(value: object, *, max_length: int) -> str:
        if not isinstance(value, str):
            raise LLMClientError("LLM response field must be text.")
        text = re.sub(r"^\s*```(?:json)?\s*", "", value.strip(), flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
        text = text.replace("**", "").replace("__", "").replace("`", "")
        text = " ".join(text.strip().split())
        if not text:
            raise LLMClientError("LLM response text was empty.")
        if len(text) > max_length:
            raise LLMClientError("LLM response text was too long.")
        lowered = text.lower()
        if any(term in lowered for term in _UNSAFE_TERMS):
            raise LLMClientError("LLM response contained unsupported safety content.")
        if any(term in lowered for term in _INTERNAL_ANALYSIS_TERMS):
            raise LLMClientError("LLM response exposed internal analysis terminology.")
        return text

    @staticmethod
    def _validated_grounding_fields(value: object) -> list[str]:
        if not isinstance(value, list):
            raise LLMClientError("grounding_fields_used must be a list.")
        fields = [field for field in value if isinstance(field, str) and field.strip()]
        if not fields:
            raise LLMClientError("grounding_fields_used cannot be empty.")
        return fields[:12]

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        deduped: list[str] = []
        for value in values:
            if value not in deduped:
                deduped.append(value)
        return deduped
