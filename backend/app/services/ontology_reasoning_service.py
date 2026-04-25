from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.engines.ontology_engine.ontology_contract import (
    BODY_PART_TAXONOMY,
    MOVEMENT_CONCEPT_TAXONOMY,
    get_ontology_mapping,
)
from app.models.enums import ComputationStatus, SeverityLevel, SkillLevel
from app.schemas.session import (
    DeterministicEvaluationIssueResponse,
    DeterministicEvaluationResult,
    FuzzyInterpretationResult,
    MetricEvaluationResultResponse,
    OntologyBodyRegionSummaryResponse,
    OntologyConceptGroupResponse,
    OntologyReasoningResult,
    OntologySeveritySummaryResponse,
    PedagogicalDecisionResult,
)

_SEVERITY_WEIGHT = {
    SeverityLevel.SEVERE: 2.0,
    SeverityLevel.MODERATE: 1.0,
}

_BODY_REGION_DISPLAY = {
    "lower_body": "lower-body",
    "upper_body": "upper-body",
    "core": "core",
}


@dataclass(frozen=True)
class _ReasoningIssue:
    metric_id: str
    phase_id: str
    severity_level: SeverityLevel
    affected_body_part: str
    computation_status: ComputationStatus


@dataclass(frozen=True)
class OntologyReasoningService:
    def build_failure_result(
        self,
        *,
        session_id,
        sport_id,
        drill_id,
        skill_level: SkillLevel,
        diagnostic_flags: list[str],
    ) -> OntologyReasoningResult:
        return OntologyReasoningResult(
            status="FAILED",
            session_id=session_id,
            sport_id=sport_id,
            drill_id=drill_id,
            skill_level=skill_level,
            primary_concept=None,
            secondary_concepts=[],
            concept_groups={},
            body_region_summary=self._build_body_region_summary(
                self._empty_body_region_state()
            ),
            reasoning_summary=(
                "Ontology reasoning could not be generated from the available artifacts."
            ),
            diagnostic_flags=self._dedupe(diagnostic_flags),
            created_at=datetime.now(UTC),
        )

    def reason(
        self,
        *,
        evaluation_result: DeterministicEvaluationResult,
        fuzzy_result: FuzzyInterpretationResult | None = None,
        pedagogical_result: PedagogicalDecisionResult | None = None,
    ) -> OntologyReasoningResult:
        diagnostic_flags = list(evaluation_result.diagnostic_flags)
        fuzzy_index: dict[tuple[str, str], object] = {}
        preferred_concept: str | None = None

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
            if (
                pedagogical_result.status == "COMPLETED"
                and pedagogical_result.learning_objective in MOVEMENT_CONCEPT_TAXONOMY
            ):
                preferred_concept = pedagogical_result.learning_objective

        concept_state: dict[str, dict[str, object]] = {}
        body_region_state = self._empty_body_region_state()

        for issue in self._iter_reasoning_issues(evaluation_result):
            if issue.computation_status is not ComputationStatus.COMPUTED:
                continue
            if issue.severity_level not in _SEVERITY_WEIGHT:
                continue

            mapping = get_ontology_mapping(issue.metric_id)
            if mapping is None:
                diagnostic_flags.append(f"ONTOLOGY_MAPPING_MISSING:{issue.metric_id}")
                continue

            fuzzy_metric = fuzzy_index.get((issue.phase_id, issue.metric_id))
            dominant_label_confidence = getattr(
                fuzzy_metric,
                "dominant_label_confidence",
                None,
            )
            weight = _SEVERITY_WEIGHT[issue.severity_level] * (
                dominant_label_confidence if dominant_label_confidence is not None else 1.0
            )
            region = self._resolve_body_region(mapping.body_part)

            region_entry = body_region_state[region]
            region_entry["concepts"].update(mapping.concepts)
            region_entry["metrics"].add(issue.metric_id)
            region_entry["phases"].add(issue.phase_id)
            region_entry["total_weight"] += weight
            if issue.severity_level is SeverityLevel.SEVERE:
                region_entry["severe_count"] += 1
            else:
                region_entry["moderate_count"] += 1

            for concept in mapping.concepts:
                concept_entry = concept_state.setdefault(
                    concept,
                    {
                        "metrics": set(),
                        "phases": set(),
                        "total_weight": 0.0,
                        "severe_count": 0,
                        "moderate_count": 0,
                    },
                )
                concept_entry["metrics"].add(issue.metric_id)
                concept_entry["phases"].add(issue.phase_id)
                concept_entry["total_weight"] += weight
                if issue.severity_level is SeverityLevel.SEVERE:
                    concept_entry["severe_count"] += 1
                else:
                    concept_entry["moderate_count"] += 1

        if not concept_state:
            return OntologyReasoningResult(
                status="NO_SIGNIFICANT_ISSUES",
                session_id=evaluation_result.session_id,
                sport_id=evaluation_result.sport_id,
                drill_id=evaluation_result.drill_id,
                skill_level=evaluation_result.skill_level,
                primary_concept=None,
                secondary_concepts=[],
                concept_groups={},
                body_region_summary=self._build_body_region_summary(body_region_state),
                reasoning_summary="No moderate or severe movement concepts were detected.",
                diagnostic_flags=self._dedupe(diagnostic_flags),
                created_at=datetime.now(UTC),
            )

        ranked_concepts = self._rank_concepts(
            concept_state=concept_state,
            preferred_concept=preferred_concept,
        )
        primary_concept = ranked_concepts[0]
        secondary_concepts = ranked_concepts[1:]
        body_region_summary = self._build_body_region_summary(body_region_state)
        return OntologyReasoningResult(
            status="COMPLETED",
            session_id=evaluation_result.session_id,
            sport_id=evaluation_result.sport_id,
            drill_id=evaluation_result.drill_id,
            skill_level=evaluation_result.skill_level,
            primary_concept=primary_concept,
            secondary_concepts=secondary_concepts,
            concept_groups=self._build_concept_groups(concept_state),
            body_region_summary=body_region_summary,
            reasoning_summary=self._build_reasoning_summary(
                primary_concept=primary_concept,
                secondary_concepts=secondary_concepts,
                body_region_summary=body_region_summary,
            ),
            diagnostic_flags=self._dedupe(diagnostic_flags),
            created_at=datetime.now(UTC),
        )

    @staticmethod
    def _iter_reasoning_issues(
        evaluation_result: DeterministicEvaluationResult,
    ) -> list[_ReasoningIssue]:
        phase_metric_results = [
            metric
            for phase in evaluation_result.phase_results
            for metric in phase.metric_results
        ]
        if phase_metric_results:
            return [
                _ReasoningIssue(
                    metric_id=metric.metric_id or metric.metric_name,
                    phase_id=metric.phase_id,
                    severity_level=metric.severity_level,
                    affected_body_part=metric.affected_body_part,
                    computation_status=metric.computation_status,
                )
                for metric in phase_metric_results
            ]

        return [
            _ReasoningIssue(
                metric_id=issue.metric_id or issue.metric_name,
                phase_id=issue.phase_id,
                severity_level=issue.severity_level,
                affected_body_part=issue.affected_body_part,
                computation_status=issue.computation_status,
            )
            for issue in evaluation_result.detected_issues
        ]

    @staticmethod
    def _resolve_body_region(body_part: str) -> str:
        for region, body_parts in BODY_PART_TAXONOMY.items():
            if body_part in body_parts:
                return region
        return "core"

    @staticmethod
    def _empty_body_region_state() -> dict[str, dict[str, object]]:
        return {
            region: {
                "concepts": set(),
                "metrics": set(),
                "phases": set(),
                "total_weight": 0.0,
                "severe_count": 0,
                "moderate_count": 0,
            }
            for region in BODY_PART_TAXONOMY
        }

    def _build_concept_groups(
        self,
        concept_state: dict[str, dict[str, object]],
    ) -> dict[str, OntologyConceptGroupResponse]:
        ranked_concepts = self._rank_concepts(
            concept_state=concept_state,
            preferred_concept=None,
        )
        return {
            concept: OntologyConceptGroupResponse(
                metrics=sorted(concept_state[concept]["metrics"]),
                phases=sorted(concept_state[concept]["phases"]),
                total_weight=round(float(concept_state[concept]["total_weight"]), 4),
                severity_summary=OntologySeveritySummaryResponse(
                    severe_count=int(concept_state[concept]["severe_count"]),
                    moderate_count=int(concept_state[concept]["moderate_count"]),
                ),
            )
            for concept in ranked_concepts
        }

    @staticmethod
    def _build_body_region_summary(
        body_region_state: dict[str, dict[str, object]],
    ) -> dict[str, OntologyBodyRegionSummaryResponse]:
        return {
            region: OntologyBodyRegionSummaryResponse(
                concepts=sorted(body_region_state[region]["concepts"]),
                metrics=sorted(body_region_state[region]["metrics"]),
                phases=sorted(body_region_state[region]["phases"]),
                total_weight=round(float(body_region_state[region]["total_weight"]), 4),
                severity_summary=OntologySeveritySummaryResponse(
                    severe_count=int(body_region_state[region]["severe_count"]),
                    moderate_count=int(body_region_state[region]["moderate_count"]),
                ),
            )
            for region in BODY_PART_TAXONOMY
        }

    @staticmethod
    def _rank_concepts(
        *,
        concept_state: dict[str, dict[str, object]],
        preferred_concept: str | None,
    ) -> list[str]:
        return sorted(
            concept_state,
            key=lambda concept: (
                -float(concept_state[concept]["total_weight"]),
                -int(concept_state[concept]["severe_count"]),
                -int(concept_state[concept]["moderate_count"]),
                0 if concept == preferred_concept else 1,
                concept,
            ),
        )

    def _build_reasoning_summary(
        self,
        *,
        primary_concept: str,
        secondary_concepts: list[str],
        body_region_summary: dict[str, OntologyBodyRegionSummaryResponse],
    ) -> str:
        dominant_region = max(
            BODY_PART_TAXONOMY,
            key=lambda region: (
                body_region_summary[region].total_weight,
                body_region_summary[region].severity_summary.severe_count,
                body_region_summary[region].severity_summary.moderate_count,
            ),
        )
        sentences = [
            (
                "Primary limitation is "
                f"{_BODY_REGION_DISPLAY[dominant_region]} "
                f"{self._display_label(primary_concept)}."
            )
        ]
        if secondary_concepts:
            secondary_text = ", ".join(
                self._display_label(concept) for concept in secondary_concepts[:2]
            )
            sentences.append(f"Secondary issue relates to {secondary_text}.")
        return " ".join(sentences)

    @staticmethod
    def _display_label(value: str) -> str:
        return value.replace("_", " ").replace("follow through", "follow-through")

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        deduped: list[str] = []
        for value in values:
            if value not in deduped:
                deduped.append(value)
        return deduped
