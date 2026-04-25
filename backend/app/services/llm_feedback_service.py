from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from app.models.enums import SeverityLevel
from app.models.training_session import TrainingSession
from app.schemas.session import (
    DeterministicEvaluationResult,
    DeterministicFeedbackItemResponse,
    DeterministicFeedbackResult,
    LLMEnhancedFeedbackItemResponse,
    LLMEnhancedSessionSummaryResponse,
    LLMFeedbackResult,
    LLM_FEEDBACK_VERSION,
    MetricEvaluationResultResponse,
)
from app.services.llm_client import LLMClient, LLMClientError, LLMMessage, LLMProviderConfig


_UNSAFE_TERMS = ("pain", "injury", "diagnose", "diagnosis", "doctor", "medical")


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
    diagnostic_flags: list[str]


@dataclass(frozen=True)
class CoachingContext:
    issue_contexts: list[CoachingIssueContext]
    summary_context: CoachingSummaryContext


@dataclass(frozen=True)
class CoachingContextBuilder:
    def build(
        self,
        *,
        session: TrainingSession,
        evaluation_result: DeterministicEvaluationResult,
        feedback_result: DeterministicFeedbackResult,
    ) -> CoachingContext:
        metric_results = self._metric_results_by_key(evaluation_result)
        strongest_area = self._ranked_metric_label(evaluation_result.strongest_metrics[:1])
        weakest_area = self._ranked_metric_label(evaluation_result.weakest_metrics[:1])
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
            ),
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

    @staticmethod
    def _build_issue_context(
        *,
        session: TrainingSession,
        evaluation_result: DeterministicEvaluationResult,
        feedback_item: DeterministicFeedbackItemResponse,
        metric_result: MetricEvaluationResultResponse | None,
        strongest_area: str | None,
        weakest_area: str | None,
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
            diagnostic_flags=evaluation_result.diagnostic_flags,
        )

    @staticmethod
    def _build_summary_context(
        *,
        session: TrainingSession,
        evaluation_result: DeterministicEvaluationResult,
        feedback_result: DeterministicFeedbackResult,
        issue_contexts: list[CoachingIssueContext],
        strongest_area: str | None,
        weakest_area: str | None,
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


@dataclass(frozen=True)
class LLMFeedbackPromptBuilder:
    def build_issue_prompt(self, context: CoachingIssueContext) -> list[LLMMessage]:
        return [
            LLMMessage(role="system", content=self._system_instruction()),
            LLMMessage(
                role="user",
                content=(
                    "Rewrite this deterministic coaching item for the athlete.\n"
                    "Use only the JSON context. Return JSON only with keys: "
                    "coaching_cue, improvement_suggestion, grounding_fields_used.\n"
                    "Each text field must be one short sentence.\n"
                    f"Context:\n{json.dumps(asdict(context), sort_keys=True)}"
                ),
            ),
        ]

    def build_summary_prompt(self, context: CoachingSummaryContext) -> list[LLMMessage]:
        return [
            LLMMessage(role="system", content=self._system_instruction()),
            LLMMessage(
                role="user",
                content=(
                    "Create a concise session summary for the athlete.\n"
                    "Use only the JSON context. Mention the highest-priority issue first, "
                    "optionally mention one strength, and give one next-step action.\n"
                    "Return JSON only with keys: summary, grounding_fields_used.\n"
                    "The summary must be no more than three short sentences.\n"
                    f"Context:\n{json.dumps(asdict(context), sort_keys=True)}"
                ),
            ),
        ]

    @staticmethod
    def _system_instruction() -> str:
        return (
            "You are a controlled sports coaching communication layer. "
            "The deterministic evaluator is the source of truth. "
            "Only explain the supplied findings. Do not invent new faults, metrics, "
            "diagnoses, pain, injury claims, or unsupported body mechanics. "
            "Do not contradict severity or priority ordering. Adapt wording to the drill, "
            "phase, and skill level. Keep language short, safe, and coaching-oriented."
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
    ) -> LLMFeedbackResult:
        context = self.context_builder.build(
            session=session,
            evaluation_result=evaluation_result,
            feedback_result=feedback_result,
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

        fallback_used = (
            enhanced_summary.fallback_used
            or any(item.fallback_used for item in enhanced_items)
            or configuration_flag is not None
        )
        return LLMFeedbackResult(
            llm_feedback_version=LLM_FEEDBACK_VERSION,
            status="COMPLETED",
            session_id=evaluation_result.session_id,
            provider=self.provider_config.provider,
            model=self.provider_config.model,
            fallback_used=fallback_used,
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
            parsed = self._call_json(
                messages=self.prompt_builder.build_issue_prompt(issue_context),
            )
            coaching_cue = self._validated_text(
                parsed.get("coaching_cue"),
                max_length=240,
            )
            improvement_suggestion = self._validated_text(
                parsed.get("improvement_suggestion"),
                max_length=240,
            )
            grounding_fields_used = self._validated_grounding_fields(
                parsed.get("grounding_fields_used")
            )
        except Exception:
            diagnostic_flags.append(
                f"LLM_ITEM_FALLBACK:{feedback_item.metric_id or feedback_item.metric_name}"
            )
            return self._fallback_item(feedback_item)

        return LLMEnhancedFeedbackItemResponse(
            phase_id=feedback_item.phase_id,
            metric_id=feedback_item.metric_id,
            metric_name=feedback_item.metric_name,
            severity_level=feedback_item.severity_level,
            priority_rank=feedback_item.priority_rank,
            affected_body_part=feedback_item.affected_body_part,
            issue_direction=feedback_item.issue_direction,
            deterministic_coaching_cue=feedback_item.coaching_cue,
            llm_coaching_cue=coaching_cue,
            deterministic_improvement_suggestion=feedback_item.improvement_suggestion,
            llm_improvement_suggestion=improvement_suggestion,
            grounding_fields_used=grounding_fields_used,
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
            diagnostic_flags.append(configuration_flag)
            return self._fallback_summary(feedback_result)

        try:
            parsed = self._call_json(
                messages=self.prompt_builder.build_summary_prompt(summary_context),
            )
            summary = self._validated_text(parsed.get("summary"), max_length=700)
            grounding_fields_used = self._validated_grounding_fields(
                parsed.get("grounding_fields_used")
            )
        except Exception:
            diagnostic_flags.append("LLM_SUMMARY_FALLBACK")
            return self._fallback_summary(feedback_result)

        return LLMEnhancedSessionSummaryResponse(
            deterministic_summary=feedback_result.overall_feedback_summary,
            llm_summary=summary,
            grounding_fields_used=grounding_fields_used,
            fallback_used=False,
        )

    def _call_json(self, *, messages: list[LLMMessage]) -> dict[str, Any]:
        raw_response = self.llm_client.generate_text(
            messages=messages,
            config=self.provider_config,
        )
        try:
            parsed = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise LLMClientError("LLM response was not valid JSON.") from exc
        if not isinstance(parsed, dict):
            raise LLMClientError("LLM response JSON must be an object.")
        return parsed

    def _configuration_fallback_flag(self) -> str | None:
        if not self.provider_config.enhancement_enabled:
            return "LLM_ENHANCEMENT_DISABLED"
        if not self.provider_config.provider:
            return "LLM_PROVIDER_NOT_CONFIGURED"
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
        text = " ".join(value.strip().split())
        if not text:
            raise LLMClientError("LLM response text was empty.")
        if len(text) > max_length:
            raise LLMClientError("LLM response text was too long.")
        lowered = text.lower()
        if any(term in lowered for term in _UNSAFE_TERMS):
            raise LLMClientError("LLM response contained unsupported safety content.")
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
