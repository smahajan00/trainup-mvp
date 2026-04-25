from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.engines.aggregation_engine.choquet_contract import (
    BODY_REGION_INTERACTION_CONFIG,
    CHOQUET_METRIC_INTENSITY_CONFIG,
    CHOQUET_VERSION,
    CONCEPT_INTERACTION_GROUPS,
    OVERALL_REGION_CHOQUET_CONFIG,
    build_capacity,
    choquet_integral,
)
from app.models.enums import ComputationStatus, SeverityLevel, SkillLevel
from app.schemas.session import (
    ChoquetAggregatedGroupResponse,
    ChoquetAggregationResult,
    DeterministicEvaluationIssueResponse,
    DeterministicEvaluationResult,
    FuzzyInterpretationResult,
    MetricEvaluationResultResponse,
    OntologyReasoningResult,
    PedagogicalDecisionResult,
)

_ACTIONABLE_SEVERITIES = {SeverityLevel.MODERATE, SeverityLevel.SEVERE}


@dataclass(frozen=True)
class _ChoquetIssue:
    metric_id: str
    phase_id: str
    severity_level: SeverityLevel
    deviation: float | None
    computation_status: ComputationStatus


@dataclass(frozen=True)
class ChoquetAggregationService:
    def build_failure_result(
        self,
        *,
        session_id,
        sport_id,
        drill_id,
        skill_level: SkillLevel,
        diagnostic_flags: list[str],
    ) -> ChoquetAggregationResult:
        return ChoquetAggregationResult(
            choquet_version=CHOQUET_VERSION,
            status="FAILED",
            session_id=session_id,
            sport_id=sport_id,
            drill_id=drill_id,
            skill_level=skill_level,
            concept_aggregation={},
            body_region_aggregation={},
            overall_choquet_score=0.0,
            dominant_interaction_group=None,
            diagnostic_flags=self._dedupe(diagnostic_flags),
            created_at=datetime.now(UTC),
        )

    def aggregate(
        self,
        *,
        evaluation_result: DeterministicEvaluationResult,
        ontology_result: OntologyReasoningResult,
        fuzzy_result: FuzzyInterpretationResult | None = None,
        pedagogical_result: PedagogicalDecisionResult | None = None,
    ) -> ChoquetAggregationResult:
        diagnostic_flags = [
            *evaluation_result.diagnostic_flags,
            *ontology_result.diagnostic_flags,
        ]
        fuzzy_index: dict[tuple[str, str], object] = {}

        if fuzzy_result is None:
            diagnostic_flags.append("MISSING_FUZZY_INTERPRETATION_RESULT")
        elif fuzzy_result.status in {"COMPLETED", "NO_INTERPRETABLE_METRICS"}:
            fuzzy_index = {
                (
                    metric.phase_id,
                    metric.metric_id or metric.metric_name,
                ): metric
                for metric in fuzzy_result.fuzzy_metric_results
            }
            diagnostic_flags.extend(fuzzy_result.diagnostic_flags)
        else:
            diagnostic_flags.extend(fuzzy_result.diagnostic_flags)
            diagnostic_flags.append(
                f"UNUSABLE_FUZZY_INTERPRETATION_RESULT:{fuzzy_result.status}"
            )

        if pedagogical_result is not None:
            diagnostic_flags.extend(pedagogical_result.diagnostic_flags)

        metric_intensities = self._build_metric_intensity_index(
            evaluation_result=evaluation_result,
            fuzzy_index=fuzzy_index,
        )
        if not metric_intensities or not ontology_result.concept_groups:
            return ChoquetAggregationResult(
                choquet_version=CHOQUET_VERSION,
                status="NO_ACTIONABLE_ISSUES",
                session_id=evaluation_result.session_id,
                sport_id=evaluation_result.sport_id,
                drill_id=evaluation_result.drill_id,
                skill_level=evaluation_result.skill_level,
                concept_aggregation={},
                body_region_aggregation={},
                overall_choquet_score=0.0,
                dominant_interaction_group=None,
                diagnostic_flags=self._dedupe(
                    [*diagnostic_flags, "NO_ACTIONABLE_ISSUES_FOR_CHOQUET"]
                ),
                created_at=datetime.now(UTC),
            )

        concept_values = self._build_concept_values(
            ontology_result=ontology_result,
            metric_intensities=metric_intensities,
        )
        concept_aggregation = self._aggregate_concept_groups(concept_values=concept_values)
        body_region_aggregation = self._aggregate_body_regions(
            ontology_result=ontology_result,
            concept_values=concept_values,
        )

        if not concept_aggregation:
            return ChoquetAggregationResult(
                choquet_version=CHOQUET_VERSION,
                status="NO_ACTIONABLE_ISSUES",
                session_id=evaluation_result.session_id,
                sport_id=evaluation_result.sport_id,
                drill_id=evaluation_result.drill_id,
                skill_level=evaluation_result.skill_level,
                concept_aggregation={},
                body_region_aggregation={},
                overall_choquet_score=0.0,
                dominant_interaction_group=None,
                diagnostic_flags=self._dedupe(
                    [*diagnostic_flags, "NO_CONCEPT_INTERACTIONS_AVAILABLE"]
                ),
                created_at=datetime.now(UTC),
            )

        overall_choquet_score = self._aggregate_overall_score(
            body_region_aggregation=body_region_aggregation,
        )
        dominant_interaction_group = self._resolve_dominant_group(
            concept_aggregation=concept_aggregation,
        )
        return ChoquetAggregationResult(
            choquet_version=CHOQUET_VERSION,
            status="COMPLETED",
            session_id=evaluation_result.session_id,
            sport_id=evaluation_result.sport_id,
            drill_id=evaluation_result.drill_id,
            skill_level=evaluation_result.skill_level,
            concept_aggregation=concept_aggregation,
            body_region_aggregation=body_region_aggregation,
            overall_choquet_score=overall_choquet_score,
            dominant_interaction_group=dominant_interaction_group,
            diagnostic_flags=self._dedupe(diagnostic_flags),
            created_at=datetime.now(UTC),
        )

    @staticmethod
    def _iter_issues(
        evaluation_result: DeterministicEvaluationResult,
    ) -> list[_ChoquetIssue]:
        phase_metric_results = [
            metric
            for phase in evaluation_result.phase_results
            for metric in phase.metric_results
        ]
        if phase_metric_results:
            return [
                _ChoquetIssue(
                    metric_id=metric.metric_id or metric.metric_name,
                    phase_id=metric.phase_id,
                    severity_level=metric.severity_level,
                    deviation=metric.deviation,
                    computation_status=metric.computation_status,
                )
                for metric in phase_metric_results
            ]

        return [
            _ChoquetIssue(
                metric_id=issue.metric_id or issue.metric_name,
                phase_id=issue.phase_id,
                severity_level=issue.severity_level,
                deviation=issue.deviation,
                computation_status=issue.computation_status,
            )
            for issue in evaluation_result.detected_issues
        ]

    def _build_metric_intensity_index(
        self,
        *,
        evaluation_result: DeterministicEvaluationResult,
        fuzzy_index: dict[tuple[str, str], object],
    ) -> dict[str, float]:
        metric_intensities: dict[str, float] = {}
        for issue in self._iter_issues(evaluation_result):
            if issue.computation_status is not ComputationStatus.COMPUTED:
                continue
            if issue.severity_level not in _ACTIONABLE_SEVERITIES:
                continue

            fuzzy_metric = fuzzy_index.get((issue.phase_id, issue.metric_id))
            intensity = self._compute_issue_intensity(
                issue=issue,
                fuzzy_metric=fuzzy_metric,
            )
            existing_intensity = metric_intensities.get(issue.metric_id, 0.0)
            metric_intensities[issue.metric_id] = max(existing_intensity, intensity)
        return metric_intensities

    def _compute_issue_intensity(
        self,
        *,
        issue: _ChoquetIssue,
        fuzzy_metric: object | None,
    ) -> float:
        base_floor = (
            CHOQUET_METRIC_INTENSITY_CONFIG.severe_floor
            if issue.severity_level is SeverityLevel.SEVERE
            else CHOQUET_METRIC_INTENSITY_CONFIG.moderate_floor
        )
        deviation_component = min(
            1.0,
            max(float(issue.deviation or 0.0), 0.0)
            / CHOQUET_METRIC_INTENSITY_CONFIG.deviation_scale,
        )
        fuzzy_component = 0.0
        if fuzzy_metric is not None:
            fuzzy_label = getattr(fuzzy_metric, "primary_fuzzy_label", "NOT_INTERPRETABLE")
            dominant_confidence = float(
                getattr(fuzzy_metric, "dominant_label_confidence", 0.0) or 0.0
            )
            fuzzy_component = min(
                1.0,
                CHOQUET_METRIC_INTENSITY_CONFIG.fuzzy_label_multipliers.get(
                    fuzzy_label,
                    0.0,
                )
                * dominant_confidence,
            )
        return round(max(base_floor, deviation_component, fuzzy_component), 4)

    @staticmethod
    def _build_concept_values(
        *,
        ontology_result: OntologyReasoningResult,
        metric_intensities: dict[str, float],
    ) -> dict[str, float]:
        concept_values: dict[str, float] = {}
        for concept, concept_group in ontology_result.concept_groups.items():
            active_metric_values = [
                metric_intensities[metric_id]
                for metric_id in concept_group.metrics
                if metric_id in metric_intensities
            ]
            if not active_metric_values:
                continue
            concept_values[concept] = round(max(active_metric_values), 4)
        return concept_values

    def _aggregate_concept_groups(
        self,
        *,
        concept_values: dict[str, float],
    ) -> dict[str, ChoquetAggregatedGroupResponse]:
        aggregation: dict[str, ChoquetAggregatedGroupResponse] = {}
        for group_id, config in CONCEPT_INTERACTION_GROUPS.items():
            input_values = {
                concept: concept_values[concept]
                for concept in config.base_concepts
                if concept in concept_values
            }
            if not input_values:
                continue

            capacity = build_capacity(
                elements=list(input_values.keys()),
                singleton_weights=config.singleton_weights,
                synergy_bonus=config.synergy_bonus,
                max_capacity=config.max_capacity,
            )
            choquet_score = choquet_integral(values=input_values, capacity=capacity)
            interaction_detected = self._interaction_detected(
                input_values=input_values,
                choquet_score=choquet_score,
            )
            aggregation[group_id] = ChoquetAggregatedGroupResponse(
                concepts=list(input_values.keys()),
                input_values=input_values,
                choquet_score=choquet_score,
                interaction_detected=interaction_detected,
                explanation=self._build_group_explanation(
                    group_id=group_id,
                    concepts=list(input_values.keys()),
                    interaction_detected=interaction_detected,
                ),
            )
        return aggregation

    def _aggregate_body_regions(
        self,
        *,
        ontology_result: OntologyReasoningResult,
        concept_values: dict[str, float],
    ) -> dict[str, ChoquetAggregatedGroupResponse]:
        aggregation: dict[str, ChoquetAggregatedGroupResponse] = {}
        for region, config in BODY_REGION_INTERACTION_CONFIG.items():
            region_summary = ontology_result.body_region_summary.get(region)
            if region_summary is None:
                continue
            input_values = {
                concept: concept_values[concept]
                for concept in region_summary.concepts
                if concept in concept_values
            }
            if not input_values:
                continue

            capacity = build_capacity(
                elements=list(input_values.keys()),
                singleton_weights=config.singleton_weights,
                synergy_bonus=config.synergy_bonus,
                max_capacity=config.max_capacity,
            )
            choquet_score = choquet_integral(values=input_values, capacity=capacity)
            interaction_detected = self._interaction_detected(
                input_values=input_values,
                choquet_score=choquet_score,
            )
            aggregation[region] = ChoquetAggregatedGroupResponse(
                concepts=list(input_values.keys()),
                input_values=input_values,
                choquet_score=choquet_score,
                interaction_detected=interaction_detected,
                explanation=self._build_region_explanation(
                    region=region,
                    concepts=list(input_values.keys()),
                    interaction_detected=interaction_detected,
                ),
            )
        return aggregation

    def _aggregate_overall_score(
        self,
        *,
        body_region_aggregation: dict[str, ChoquetAggregatedGroupResponse],
    ) -> float:
        if not body_region_aggregation:
            return 0.0
        region_values = {
            region: payload.choquet_score
            for region, payload in body_region_aggregation.items()
        }
        capacity = build_capacity(
            elements=list(region_values.keys()),
            singleton_weights=OVERALL_REGION_CHOQUET_CONFIG.singleton_weights,
            synergy_bonus=OVERALL_REGION_CHOQUET_CONFIG.synergy_bonus,
            max_capacity=OVERALL_REGION_CHOQUET_CONFIG.max_capacity,
        )
        return choquet_integral(values=region_values, capacity=capacity)

    @staticmethod
    def _resolve_dominant_group(
        *,
        concept_aggregation: dict[str, ChoquetAggregatedGroupResponse],
    ) -> str | None:
        if not concept_aggregation:
            return None
        return max(
            concept_aggregation,
            key=lambda group_id: (
                concept_aggregation[group_id].choquet_score,
                len(concept_aggregation[group_id].concepts),
                group_id,
            ),
        )

    @staticmethod
    def _interaction_detected(
        *,
        input_values: dict[str, float],
        choquet_score: float,
    ) -> bool:
        if len(input_values) < 2:
            return False
        mean_score = sum(input_values.values()) / len(input_values)
        return choquet_score > round(mean_score, 4)

    def _build_group_explanation(
        self,
        *,
        group_id: str,
        concepts: list[str],
        interaction_detected: bool,
    ) -> str:
        display_group = group_id.replace("_", " ")
        display_concepts = self._display_items(concepts)
        if len(concepts) < 2:
            return f"{display_group.capitalize()} reflects the strongest issue in {display_concepts}."
        if interaction_detected:
            return (
                f"{display_group.capitalize()} is elevated because {display_concepts} "
                "appeared together."
            )
        return f"{display_group.capitalize()} is driven by the strongest issue in {display_concepts}."

    def _build_region_explanation(
        self,
        *,
        region: str,
        concepts: list[str],
        interaction_detected: bool,
    ) -> str:
        display_region = region.replace("_", "-")
        display_concepts = self._display_items(concepts)
        if len(concepts) < 2:
            return f"{display_region.capitalize()} aggregation reflects {display_concepts}."
        if interaction_detected:
            return (
                f"{display_region.capitalize()} aggregation is elevated because "
                f"{display_concepts} interacted."
            )
        return f"{display_region.capitalize()} aggregation reflects the strongest issue in {display_concepts}."

    @staticmethod
    def _display_items(values: list[str]) -> str:
        return ", ".join(value.replace("_", " ") for value in values)

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        deduped: list[str] = []
        for value in values:
            if value not in deduped:
                deduped.append(value)
        return deduped
