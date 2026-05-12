from __future__ import annotations

import json
import logging
from uuid import UUID

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.core.dependencies import get_llm_feedback_service
from app.main import app
from app.models.drill import Drill
from app.models.enums import SeverityLevel
from app.models.session_artifact import SessionArtifact
from app.models.training_session import TrainingSession
from app.schemas.session import (
    ChoquetAggregatedGroupResponse,
    ChoquetAggregationResult,
    DeterministicEvaluationIssueResponse,
    DeterministicEvaluationResult,
    DeterministicFeedbackResult,
    EvaluationFrameRangeResponse,
    FuzzyInterpretationResult,
    FuzzyMetricInterpretationResponse,
    FuzzySummaryResponse,
    IT2FuzzyInterpretationResult,
    IT2FuzzyMetricInterpretationResponse,
    IT2HighestUncertaintyMetricResponse,
    IT2MembershipIntervalResponse,
    IT2UncertaintySummaryResponse,
    MetricEvaluationResultResponse,
    OntologyBodyRegionSummaryResponse,
    OntologyConceptGroupResponse,
    OntologyReasoningResult,
    OntologySeveritySummaryResponse,
    PedagogicalDecisionResult,
    PedagogicalFocusItemResponse,
    PedagogicalSuppressedItemResponse,
    PhaseEvaluationResultResponse,
    RankedMetricResponse,
    TemporalModelingResult,
    TemporalPhaseResultResponse,
    TemporalTransitionResultResponse,
)
from app.services.deterministic_feedback_service import DeterministicFeedbackService
from app.services.llm_client import LLMClientError, LLMMessage, LLMProviderConfig
from app.services.llm_feedback_service import (
    CoachingContextBuilder,
    LLMFeedbackPromptBuilder,
    LLMFeedbackService,
)


class FakeLLMClient:
    def __init__(self, responses: list[str] | None = None, *, fail: bool = False) -> None:
        self.responses = responses or []
        self.fail = fail
        self.calls: list[list[LLMMessage]] = []

    def generate_text(
        self,
        *,
        messages: list[LLMMessage],
        config: LLMProviderConfig,
    ) -> str:
        self.calls.append(messages)
        if self.fail:
            raise LLMClientError("fake provider failure")
        if not self.responses:
            raise LLMClientError("no fake response configured")
        return self.responses.pop(0)


def _provider_config(
    *,
    enabled: bool = True,
    api_key: str | None = "test-key",
    provider: str = "gemini",
    model: str = "gemini-2.5-flash",
) -> LLMProviderConfig:
    return LLMProviderConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url="https://llm.example.test/v1",
        timeout_seconds=2.0,
        temperature=0.1,
        max_tokens=300,
        enhancement_enabled=enabled,
    )


def _llm_service(
    fake_client: FakeLLMClient,
    *,
    config: LLMProviderConfig | None = None,
) -> LLMFeedbackService:
    return LLMFeedbackService(
        llm_client=fake_client,
        provider_config=config or _provider_config(),
        context_builder=CoachingContextBuilder(),
        prompt_builder=LLMFeedbackPromptBuilder(),
    )


def _register_user(client, *, email: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Phase 3B LLM",
            "email": email,
            "password": "strongpass123",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def _get_drill(db_session, drill_name: str) -> Drill:
    drill = db_session.scalar(select(Drill).where(Drill.drill_name == drill_name))
    assert drill is not None
    return drill


def _create_session(client, token: str, drill: Drill) -> dict[str, str]:
    capture_protocol = (drill.reference_payload or {}).get("capture_protocol", {})
    allowed_views = capture_protocol.get("allowed_camera_views", [])
    camera_view = capture_protocol.get("canonical_view") or (
        allowed_views[0] if allowed_views else None
    )
    payload = {
        "sport_id": str(drill.sport_id),
        "skill_level": "BEGINNER",
        "drill_id": str(drill.id),
        "input_type": "UPLOAD",
    }
    if camera_view is not None:
        payload["camera_view"] = camera_view
    if drill.drill_name == "Set Shot Form":
        payload["dominant_side"] = "RIGHT"

    response = client.post(
        "/api/sessions",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


def _evaluation_result(session_id: str, drill: Drill) -> DeterministicEvaluationResult:
    issue = DeterministicEvaluationIssueResponse(
        phase_id="descent",
        metric_id="knee_alignment_score",
        metric_name="knee_alignment_score",
        severity_level=SeverityLevel.SEVERE,
        affected_body_part="knees",
        deviation=0.24,
        issue_direction="UNDER_RANGE",
    )
    metric_result = MetricEvaluationResultResponse(
        metric_id="knee_alignment_score",
        metric_name="knee_alignment_score",
        phase_id="descent",
        raw_value=0.58,
        unit="score",
        ideal_min=0.78,
        ideal_max=1.0,
        deviation=0.20,
        issue_direction="UNDER_RANGE",
        severity_level=SeverityLevel.SEVERE,
        normalized_score=0.58,
        affected_body_part="knees",
        computation_status="COMPUTED",
        valid_frame_count=12,
        formula_version="phase0_v0_1_0",
        diagnostic_flags=[],
    )
    return DeterministicEvaluationResult(
        status="COMPLETED",
        session_id=UUID(session_id),
        sport_id=drill.sport_id,
        skill_level="BEGINNER",
        drill_id=drill.id,
        phase_results=[
            PhaseEvaluationResultResponse(
                phase_id="descent",
                frame_range=EvaluationFrameRangeResponse(
                    phase_id="descent",
                    start_frame_index=5,
                    end_frame_index=20,
                    start_timestamp_ms=166.5,
                    end_timestamp_ms=666.0,
                ),
                metric_results=[metric_result],
                phase_score=0.58,
                phase_severity=SeverityLevel.SEVERE,
                detected_issues=[issue],
            )
        ],
        overall_score=0.68,
        overall_severity=SeverityLevel.SEVERE,
        detected_issues=[issue],
        strongest_metrics=[
            RankedMetricResponse(
                phase_id="setup",
                metric_id="posture_accuracy",
                metric_name="posture_accuracy",
                score=0.92,
            )
        ],
        weakest_metrics=[
            RankedMetricResponse(
                phase_id="descent",
                metric_id="knee_alignment_score",
                metric_name="knee_alignment_score",
                score=0.58,
            )
        ],
        diagnostic_flags=[],
    )


def _store_feedback_inputs(
    db_session,
    *,
    session_id: str,
    drill: Drill,
) -> tuple[DeterministicEvaluationResult, DeterministicFeedbackResult]:
    evaluation_result = _evaluation_result(session_id, drill)
    feedback_result = DeterministicFeedbackService().generate(
        evaluation_result=evaluation_result
    )
    for artifact_type, payload in (
        ("evaluation_result", evaluation_result.model_dump(mode="json")),
        ("feedback_result", feedback_result.model_dump(mode="json")),
    ):
        db_session.add(
            SessionArtifact(
                session_id=UUID(session_id),
                artifact_type=artifact_type,
                payload_json=payload,
            )
        )
    db_session.commit()
    return evaluation_result, feedback_result


def _build_advanced_artifacts(
    *,
    session_id: str,
    drill: Drill,
):
    session_uuid = UUID(session_id)
    fuzzy_result = FuzzyInterpretationResult(
        status="COMPLETED",
        session_id=session_uuid,
        drill_id=drill.id,
        sport_id=drill.sport_id,
        skill_level="BEGINNER",
        fuzzy_metric_results=[
            FuzzyMetricInterpretationResponse(
                metric_id="knee_alignment_score",
                metric_name="knee_alignment_score",
                phase_id="descent",
                computation_status="COMPUTED",
                deviation=0.24,
                issue_direction="UNDER_RANGE",
                severity_level=SeverityLevel.SEVERE,
                affected_body_part="knees",
                primary_fuzzy_label="STRONGLY_OFF",
                membership_scores={
                    "IDEAL": 0.0,
                    "SLIGHTLY_OFF": 0.1,
                    "MODERATELY_OFF": 0.35,
                    "STRONGLY_OFF": 0.75,
                },
                dominant_label_confidence=0.75,
                direction_aware_label="STRONGLY_LOW",
                diagnostic_flags=[],
            )
        ],
        fuzzy_summary=FuzzySummaryResponse(
            ideal_count=0,
            slightly_off_count=0,
            moderately_off_count=0,
            strongly_off_count=1,
            not_interpretable_count=0,
            interpretable_metric_count=1,
            dominant_fuzzy_label="STRONGLY_OFF",
            top_concern_areas=["knees"],
        ),
        diagnostic_flags=[],
    )
    it2_result = IT2FuzzyInterpretationResult(
        status="COMPLETED",
        session_id=session_uuid,
        sport_id=drill.sport_id,
        drill_id=drill.id,
        skill_level="BEGINNER",
        it2_metric_results=[
            IT2FuzzyMetricInterpretationResponse(
                phase_id="descent",
                metric_id="knee_alignment_score",
                metric_name="knee_alignment_score",
                computation_status="COMPUTED",
                deviation=0.24,
                issue_direction="UNDER_RANGE",
                severity_level=SeverityLevel.SEVERE,
                affected_body_part="knees",
                type1_primary_label="STRONGLY_OFF",
                type1_direction_aware_label="STRONGLY_LOW",
                dominant_label_confidence=0.75,
                uncertainty_width=0.18,
                uncertainty_category="MEDIUM_UNCERTAINTY",
                interval_memberships={
                    "IDEAL": IT2MembershipIntervalResponse(lower=0.0, upper=0.18, width=0.18),
                    "SLIGHTLY_OFF": IT2MembershipIntervalResponse(
                        lower=0.0, upper=0.28, width=0.28
                    ),
                    "MODERATELY_OFF": IT2MembershipIntervalResponse(
                        lower=0.17, upper=0.53, width=0.36
                    ),
                    "STRONGLY_OFF": IT2MembershipIntervalResponse(
                        lower=0.57, upper=0.93, width=0.36
                    ),
                },
                primary_interval_label="STRONGLY_OFF",
                diagnostic_flags=[],
            )
        ],
        uncertainty_summary=IT2UncertaintySummaryResponse(
            low_count=0,
            medium_count=1,
            high_count=0,
            not_interpretable_count=0,
            average_uncertainty_width=0.18,
            highest_uncertainty_metric=IT2HighestUncertaintyMetricResponse(
                phase_id="descent",
                metric_id="knee_alignment_score",
                uncertainty_width=0.18,
            ),
            summary_text="Most interpretations have moderate certainty.",
        ),
        diagnostic_flags=[],
    )
    pedagogical_result = PedagogicalDecisionResult(
        status="COMPLETED",
        session_id=session_uuid,
        sport_id=drill.sport_id,
        drill_id=drill.id,
        skill_level="BEGINNER",
        teaching_strategy="single_focus_mastery",
        selected_focus_items=[
            PedagogicalFocusItemResponse(
                phase_id="descent",
                metric_id="knee_alignment_score",
                metric_name="knee_alignment_score",
                severity_level=SeverityLevel.SEVERE,
                fuzzy_label="STRONGLY_OFF",
                dominant_label_confidence=0.75,
                affected_body_part="knees",
                priority_rank=1,
                teaching_reason="This is the clearest high-priority movement issue.",
                recommended_message_style="supportive_simple",
            )
        ],
        suppressed_items=[
            PedagogicalSuppressedItemResponse(
                phase_id="setup",
                metric_id="posture_accuracy",
                metric_name="posture_accuracy",
                severity_level=SeverityLevel.MINOR,
                priority_rank=2,
                suppression_reason="Keep the focus on one correction first.",
            )
        ],
        tone_profile="supportive_simple",
        correction_intensity="direct",
        learning_objective="alignment",
        progression_advice="Repeat the drill with one clear focus on knee tracking.",
        diagnostic_flags=[],
    )
    severity_summary = OntologySeveritySummaryResponse(severe_count=1, moderate_count=0)
    ontology_result = OntologyReasoningResult(
        status="COMPLETED",
        session_id=session_uuid,
        sport_id=drill.sport_id,
        drill_id=drill.id,
        skill_level="BEGINNER",
        primary_concept="alignment",
        secondary_concepts=["control"],
        concept_groups={
            "alignment": OntologyConceptGroupResponse(
                metrics=["knee_alignment_score"],
                phases=["descent"],
                total_weight=1.0,
                severity_summary=severity_summary,
            )
        },
        body_region_summary={
            "lower_body": OntologyBodyRegionSummaryResponse(
                concepts=["alignment"],
                metrics=["knee_alignment_score"],
                phases=["descent"],
                total_weight=1.0,
                severity_summary=severity_summary,
            )
        },
        reasoning_summary="Primary limitation is lower-body alignment control.",
        diagnostic_flags=[],
    )
    choquet_result = ChoquetAggregationResult(
        status="COMPLETED",
        session_id=session_uuid,
        sport_id=drill.sport_id,
        drill_id=drill.id,
        skill_level="BEGINNER",
        concept_aggregation={
            "lower_body_control": ChoquetAggregatedGroupResponse(
                concepts=["alignment", "control"],
                input_values={"alignment": 0.82, "control": 0.64},
                choquet_score=0.88,
                interaction_detected=True,
                explanation="Related lower-body issues appeared together.",
            )
        },
        body_region_aggregation={
            "lower_body": ChoquetAggregatedGroupResponse(
                concepts=["alignment", "control"],
                input_values={"alignment": 0.82, "control": 0.64},
                choquet_score=0.88,
                interaction_detected=True,
                explanation="Lower-body control is elevated by interacting issues.",
            )
        },
        overall_choquet_score=0.88,
        dominant_interaction_group="lower_body_control",
        diagnostic_flags=[],
    )
    temporal_result = TemporalModelingResult(
        status="COMPLETED",
        session_id=session_uuid,
        sport_id=drill.sport_id,
        drill_id=drill.id,
        skill_level="BEGINNER",
        phase_temporal_results=[
            TemporalPhaseResultResponse(
                phase_id="descent",
                frame_count=16,
                phase_duration_ms=499.5,
                valid_frame_ratio=1.0,
                average_velocity_proxy=0.78,
                smoothness_proxy=0.31,
                acceleration_change_proxy=0.62,
                temporal_state="RUSHED",
                state_confidence=0.81,
                diagnostic_flags=[],
            )
        ],
        transition_results=[
            TemporalTransitionResultResponse(
                from_phase="setup",
                to_phase="descent",
                transition_valid=True,
                transition_gap_ms=0.0,
                phase_order_valid=True,
                diagnostic_flags=[],
            )
        ],
        overall_temporal_state="RUSHED",
        temporal_summary="The movement looked rushed during descent.",
        diagnostic_flags=[],
    )
    return {
        "fuzzy_interpretation_result": fuzzy_result,
        "it2_fuzzy_interpretation_result": it2_result,
        "pedagogical_decision_result": pedagogical_result,
        "ontology_reasoning_result": ontology_result,
        "choquet_aggregation_result": choquet_result,
        "temporal_modeling_result": temporal_result,
    }


def _store_advanced_context_artifacts(
    db_session,
    *,
    session_id: str,
    drill: Drill,
):
    artifacts = _build_advanced_artifacts(session_id=session_id, drill=drill)
    for artifact_type, payload in artifacts.items():
        db_session.add(
            SessionArtifact(
                session_id=UUID(session_id),
                artifact_type=artifact_type,
                payload_json=payload.model_dump(mode="json"),
            )
        )
    db_session.commit()
    return artifacts


def test_phase3b_provider_config_reads_settings() -> None:
    settings = Settings(
        llm_provider="gemini",
        llm_model="gemini-2.5-flash",
        gemini_api_key="gemini-key",
        llm_api_key="abc",
        llm_base_url="http://localhost:11434/v1",
        llm_timeout_seconds=3.5,
        llm_temperature=0.0,
        llm_max_tokens=220,
        llm_enable_enhancement=True,
    )

    config = LLMProviderConfig.from_settings(settings)

    assert config.provider == "gemini"
    assert config.model == "gemini-2.5-flash"
    assert config.api_key == "gemini-key"
    assert config.base_url == "http://localhost:11434/v1"
    assert config.timeout_seconds == 3.5
    assert config.temperature == 0.0
    assert config.max_tokens == 220
    assert config.enhancement_enabled is True


def test_phase3b_gemini_provider_requires_api_key() -> None:
    service = _llm_service(
        FakeLLMClient(),
        config=_provider_config(
            api_key=None,
            enabled=True,
        ),
    )

    assert service._configuration_fallback_flag() == "LLM_API_KEY_MISSING"


def test_phase3b_raw_json_response_is_supported() -> None:
    service = _llm_service(
        FakeLLMClient(
            responses=[
                '{"summary":"Keep the next rep steady.","grounding_fields_used":["deterministic_feedback"]}'
            ]
        )
    )

    parsed = service._call_json(messages=[LLMMessage(role="user", content="compact context")])

    assert parsed == {
        "summary": "Keep the next rep steady.",
        "grounding_fields_used": ["deterministic_feedback"],
    }


def test_phase3b_fenced_json_response_is_supported() -> None:
    service = _llm_service(
        FakeLLMClient(
            responses=[
                """```json
{"summary":"Keep the next rep controlled.","grounding_fields_used":["deterministic_feedback"]}
```"""
            ]
        )
    )

    parsed = service._call_json(messages=[LLMMessage(role="user", content="compact context")])

    assert parsed == {
        "summary": "Keep the next rep controlled.",
        "grounding_fields_used": ["deterministic_feedback"],
    }


def test_phase3b_plain_fenced_json_response_is_supported() -> None:
    service = _llm_service(
        FakeLLMClient(
            responses=[
                """```
{"summary":"Keep the next rep smooth.","grounding_fields_used":["deterministic_feedback"]}
```"""
            ]
        )
    )

    parsed = service._call_json(messages=[LLMMessage(role="user", content="compact context")])

    assert parsed == {
        "summary": "Keep the next rep smooth.",
        "grounding_fields_used": ["deterministic_feedback"],
    }


def test_phase3b_extra_text_around_json_response_is_supported() -> None:
    service = _llm_service(
        FakeLLMClient(
            responses=[
                """Here is the JSON:
{"summary":"Keep one steady knee cue.","grounding_fields_used":["deterministic_feedback"]}
Use this for the athlete."""
            ]
        )
    )

    parsed = service._call_json(
        messages=[LLMMessage(role="user", content="compact context")],
        required_keys=frozenset({"summary", "grounding_fields_used"}),
    )

    assert parsed == {
        "summary": "Keep one steady knee cue.",
        "grounding_fields_used": ["deterministic_feedback"],
    }


def test_phase3b_prefix_plus_fenced_json_response_is_supported() -> None:
    service = _llm_service(
        FakeLLMClient(
            responses=[
                """Here is the JSON requested:
```json
{"summary":"Keep one clean correction.","grounding_fields_used":["top_issue"]}
```"""
            ]
        )
    )

    parsed = service._call_json(
        messages=[LLMMessage(role="user", content="compact context")],
        required_keys=frozenset({"summary", "grounding_fields_used"}),
    )

    assert parsed == {
        "summary": "Keep one clean correction.",
        "grounding_fields_used": ["top_issue"],
    }


def test_phase3b_balanced_json_extraction_ignores_braces_inside_strings() -> None:
    service = _llm_service(
        FakeLLMClient(
            responses=[
                'Here is the JSON: {"summary":"Keep the cue {inside the same sentence} and move steadily.","grounding_fields_used":["deterministic_feedback"]}'
            ]
        )
    )

    parsed = service._call_json(
        messages=[LLMMessage(role="user", content="compact context")],
        required_keys=frozenset({"summary", "grounding_fields_used"}),
    )

    assert parsed == {
        "summary": "Keep the cue {inside the same sentence} and move steadily.",
        "grounding_fields_used": ["deterministic_feedback"],
    }


def test_phase3b_json_parse_failure_logs_safe_reason(caplog) -> None:
    service = _llm_service(FakeLLMClient(responses=["not-json"]))
    caplog.set_level(logging.WARNING)

    with pytest.raises(LLMClientError, match="not valid JSON"):
        service._call_json(messages=[LLMMessage(role="user", content="compact context")])

    assert "LLM JSON parse failed" in caplog.text
    assert "parse_error=No JSON object found in LLM response" in caplog.text
    assert "position=0" in caplog.text
    assert "response_preview=not-json" in caplog.text
    assert "compact context" not in caplog.text


def test_phase3b_llm_enabled_alias_overrides_legacy_flag() -> None:
    settings = Settings(
        llm_enabled=True,
        llm_enable_enhancement=False,
    )

    config = LLMProviderConfig.from_settings(settings)

    assert config.enhancement_enabled is True


def test_phase3b_context_builder_includes_grounded_fields(client, db_session) -> None:
    token = _register_user(client, email="phase3b-context@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session_payload = _create_session(client, token, drill)
    evaluation_result, feedback_result = _store_feedback_inputs(
        db_session,
        session_id=session_payload["id"],
        drill=drill,
    )
    session = db_session.get(TrainingSession, UUID(session_payload["id"]))
    assert session is not None

    context = CoachingContextBuilder().build(
        session=session,
        evaluation_result=evaluation_result,
        feedback_result=feedback_result,
    )

    issue_context = context.issue_contexts[0]
    assert issue_context.drill_name == "Bodyweight Squat"
    assert issue_context.skill_level == "BEGINNER"
    assert issue_context.phase_id == "descent"
    assert issue_context.metric_id == "knee_alignment_score"
    assert issue_context.raw_value == 0.58
    assert issue_context.ideal_min == 0.78
    assert issue_context.deviation == 0.24
    assert issue_context.deterministic_coaching_cue == "Keep both knees tracking over the middle toes."
    assert context.summary_context.top_issue is not None
    assert context.summary_context.strongest_area == "posture_accuracy in setup"


def test_phase3b_context_builder_includes_advanced_reasoning_context(
    client,
    db_session,
) -> None:
    token = _register_user(client, email="phase3b-advanced-context@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session_payload = _create_session(client, token, drill)
    evaluation_result, feedback_result = _store_feedback_inputs(
        db_session,
        session_id=session_payload["id"],
        drill=drill,
    )
    advanced_artifacts = _build_advanced_artifacts(
        session_id=session_payload["id"],
        drill=drill,
    )
    session = db_session.get(TrainingSession, UUID(session_payload["id"]))
    assert session is not None

    context = CoachingContextBuilder().build(
        session=session,
        evaluation_result=evaluation_result,
        feedback_result=feedback_result,
        fuzzy_result=advanced_artifacts["fuzzy_interpretation_result"],
        it2_fuzzy_result=advanced_artifacts["it2_fuzzy_interpretation_result"],
        pedagogical_result=advanced_artifacts["pedagogical_decision_result"],
        ontology_result=advanced_artifacts["ontology_reasoning_result"],
        choquet_result=advanced_artifacts["choquet_aggregation_result"],
        temporal_result=advanced_artifacts["temporal_modeling_result"],
    )

    assert context.advanced_context_used is True
    assert context.advanced_context_sources == [
        "fuzzy_interpretation_result",
        "it2_fuzzy_interpretation_result",
        "pedagogical_decision_result",
        "ontology_reasoning_result",
        "choquet_aggregation_result",
        "temporal_modeling_result",
    ]

    issue_context = context.issue_contexts[0]
    advanced_issue = issue_context.advanced_reasoning_context
    assert advanced_issue["fuzzy"] == {
        "top_metric_label": "STRONGLY_OFF",
        "direction_aware_label": "STRONGLY_LOW",
        "dominant_label_confidence": 0.75,
    }
    assert advanced_issue["it2_uncertainty"] == {
        "uncertainty_category": "MEDIUM_UNCERTAINTY",
        "uncertainty_width": 0.18,
        "confidence_guidance": "moderate_certainty",
    }
    assert advanced_issue["pedagogy"]["teaching_strategy"] == "single_focus_mastery"
    assert advanced_issue["pedagogy"]["tone_profile"] == "supportive_simple"
    assert advanced_issue["pedagogy"]["correction_intensity"] == "direct"
    assert advanced_issue["pedagogy"]["learning_objective"] == "alignment"
    assert (
        advanced_issue["pedagogy"]["progression_advice"]
        == "Repeat the drill with one clear focus on knee tracking."
    )
    assert advanced_issue["pedagogy"]["selected_focus"] is True
    assert advanced_issue["pedagogy"]["recommended_message_style"] == "supportive_simple"
    assert advanced_issue["ontology"]["primary_concept"] == "alignment"
    assert advanced_issue["ontology"]["primary_body_region"] == "lower_body"
    assert advanced_issue["ontology"]["reasoning_summary"] == "Primary limitation is lower-body alignment control."
    assert advanced_issue["ontology"]["concepts"] == ["alignment"]
    assert advanced_issue["choquet"] == {
        "dominant_interaction_group": "lower_body_control",
        "overall_choquet_score": 0.88,
        "interaction_summary": "Related lower-body issues appeared together.",
    }
    assert advanced_issue["temporal"] == {
        "overall_temporal_state": "RUSHED",
        "top_phase_temporal_state": "RUSHED",
        "temporal_summary": "The movement looked rushed during descent.",
    }

    summary_context = context.summary_context.advanced_reasoning_context
    assert summary_context["ontology"]["primary_concept"] == "alignment"
    assert summary_context["choquet"]["dominant_interaction_group"] == "lower_body_control"
    assert summary_context["temporal"]["overall_temporal_state"] == "RUSHED"
    assert (
        summary_context["pedagogy"]["progression_advice"]
        == "Repeat the drill with one clear focus on knee tracking."
    )
    assert summary_context["it2_uncertainty"]["average_uncertainty_width"] == 0.18
    assert summary_context["it2_uncertainty"]["confidence_guidance"] == "moderate_certainty"


def test_phase3b_prompts_include_deterministic_facts(client, db_session) -> None:
    token = _register_user(client, email="phase3b-prompts@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session_payload = _create_session(client, token, drill)
    evaluation_result, feedback_result = _store_feedback_inputs(
        db_session,
        session_id=session_payload["id"],
        drill=drill,
    )
    session = db_session.get(TrainingSession, UUID(session_payload["id"]))
    context = CoachingContextBuilder().build(
        session=session,
        evaluation_result=evaluation_result,
        feedback_result=feedback_result,
    )

    messages = LLMFeedbackPromptBuilder().build_issue_prompt(context.issue_contexts[0])
    prompt_text = "\n".join(message.content for message in messages)

    assert "deterministic evaluator is the source of truth" in prompt_text.lower()
    assert "Bodyweight Squat" in prompt_text
    assert "BEGINNER" in prompt_text
    assert "knee_alignment_score" in prompt_text
    assert "Keep both knees tracking over the middle toes." in prompt_text
    assert "Return three short lines in plain text" in prompt_text
    assert "Main cue:" in prompt_text
    assert "Fix:" in prompt_text
    assert "Next session cue:" in prompt_text
    assert "Do not return JSON" in prompt_text
    assert "raw_value" not in prompt_text
    assert "pose_sequence" not in prompt_text
    assert "If uncertainty is high, use softer wording" in prompt_text
    assert "Fuzzy context: use linguistic movement severity" in prompt_text
    assert "Movement concept context: explain related body concepts naturally" in prompt_text
    assert "Linked-issue context: if related issues appeared together" in prompt_text
    assert "Timing context: if state is RUSHED, JERKY, CONTROLLED, or STABLE" in prompt_text
    assert "Do not mention internal terms like ontology, Choquet, IT2 fuzzy, temporal model, or diagnostic flags." in prompt_text


def test_phase3b_summary_prompt_includes_advanced_reasoning_guidance(client, db_session) -> None:
    token = _register_user(client, email="phase3b-summary-prompt@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session_payload = _create_session(client, token, drill)
    evaluation_result, feedback_result = _store_feedback_inputs(
        db_session,
        session_id=session_payload["id"],
        drill=drill,
    )
    advanced_artifacts = _build_advanced_artifacts(
        session_id=session_payload["id"],
        drill=drill,
    )
    session = db_session.get(TrainingSession, UUID(session_payload["id"]))
    assert session is not None

    context = CoachingContextBuilder().build(
        session=session,
        evaluation_result=evaluation_result,
        feedback_result=feedback_result,
        fuzzy_result=advanced_artifacts["fuzzy_interpretation_result"],
        it2_fuzzy_result=advanced_artifacts["it2_fuzzy_interpretation_result"],
        pedagogical_result=advanced_artifacts["pedagogical_decision_result"],
        ontology_result=advanced_artifacts["ontology_reasoning_result"],
        choquet_result=advanced_artifacts["choquet_aggregation_result"],
        temporal_result=advanced_artifacts["temporal_modeling_result"],
    )

    messages = LLMFeedbackPromptBuilder().build_summary_prompt(context.summary_context)
    prompt_text = "\n".join(message.content for message in messages)

    assert "Use deterministic evaluation as the source of truth." in prompt_text
    assert "Return plain text only" in prompt_text
    assert "Do not return JSON" in prompt_text
    assert "Do not add issues, body regions, metrics, causes, or priorities that are not present in context." in prompt_text
    assert "Use advanced reasoning only to refine wording, explanation, prioritization, and coaching clarity." in prompt_text
    assert "Fuzzy context: use linguistic movement severity" in prompt_text
    assert "Uncertainty context: if confidence guidance is low_certainty" in prompt_text
    assert "Pedagogy context: match cue complexity to skill level" in prompt_text
    assert "Movement concept context: explain related body concepts naturally" in prompt_text
    assert "Linked-issue context: if related issues appeared together" in prompt_text
    assert "Timing context: if state is RUSHED, JERKY, CONTROLLED, or STABLE" in prompt_text
    assert "Do not mention internal terms like ontology, Choquet, IT2 fuzzy, temporal model, or diagnostic flags." in prompt_text
    assert "advanced_reasoning_summaries" in prompt_text


def test_phase3b_successful_fake_provider_preserves_deterministic_fields(
    client,
    db_session,
) -> None:
    token = _register_user(client, email="phase3b-success@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)
    _store_feedback_inputs(db_session, session_id=session["id"], drill=drill)
    fake_client = FakeLLMClient(
        responses=[
            (
                "Main cue: During the squat descent, keep both knees tracking over your toes.\n"
                "Fix: Slow the descent and press the knees outward before standing up.\n"
                "Next session cue: On the next set, move slowly and repeat the same knee line."
            ),
            "Your squat setup was steady, but the descent needs attention first. Keep the knees tracking over the toes and slow the next rep.",
        ]
    )
    app.dependency_overrides[get_llm_feedback_service] = lambda: _llm_service(fake_client)

    response = client.post(
        f"/api/sessions/{session['id']}/feedback/llm",
        headers={"Authorization": f"Bearer {token}"},
    )
    app.dependency_overrides.pop(get_llm_feedback_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "llm_feedback_version",
        "status",
        "session_id",
        "provider",
        "model",
        "fallback_used",
        "advanced_context_used",
        "advanced_context_sources",
        "context_diagnostic_flags",
        "enhanced_feedback_items",
        "enhanced_summary",
        "diagnostic_flags",
        "created_at",
    }
    assert payload["llm_feedback_version"] == "phase3b_v0_1_0"
    assert payload["provider"] == "gemini"
    assert payload["model"] == "gemini-2.5-flash"
    assert payload["fallback_used"] is False
    assert payload["advanced_context_used"] is False
    assert payload["advanced_context_sources"] == []
    assert payload["context_diagnostic_flags"] == [
        "ADVANCED_CONTEXT_MISSING:fuzzy_interpretation_result",
        "ADVANCED_CONTEXT_MISSING:it2_fuzzy_interpretation_result",
        "ADVANCED_CONTEXT_MISSING:pedagogical_decision_result",
        "ADVANCED_CONTEXT_MISSING:ontology_reasoning_result",
        "ADVANCED_CONTEXT_MISSING:choquet_aggregation_result",
        "ADVANCED_CONTEXT_MISSING:temporal_modeling_result",
    ]
    item = payload["enhanced_feedback_items"][0]
    assert item["metric_id"] == "knee_alignment_score"
    assert item["deterministic_coaching_cue"] == "Keep both knees tracking over the middle toes."
    assert "squat descent" in item["llm_coaching_cue"]
    assert item["llm_what_happened"]
    assert item["llm_why_it_matters"]
    assert "Slow the descent" in item["llm_what_to_fix"]
    assert "next set" in item["llm_next_session_cue"]
    assert item["fallback_used"] is False

    artifact = db_session.scalar(
        select(SessionArtifact).where(
            SessionArtifact.session_id == session["id"],
            SessionArtifact.artifact_type == "llm_feedback_result",
        )
    )
    assert artifact is not None
    assert artifact.payload_json["provider"] == "gemini"
    assert len(fake_client.calls) == 2


def test_phase3b_fenced_gemini_success_does_not_fall_back(client, db_session) -> None:
    token = _register_user(client, email="phase3b-fenced-success@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)
    _store_feedback_inputs(db_session, session_id=session["id"], drill=drill)
    fake_client = FakeLLMClient(
        responses=[
            """```
Main cue: Keep your knees steady as you lower into the squat.
Fix: Slow the descent and keep the knees over the middle toes.
Next session cue: On the next set, repeat the same knee line for each rep.
```""",
            "Your main focus is steady knee tracking during the squat descent.",
        ]
    )
    app.dependency_overrides[get_llm_feedback_service] = lambda: _llm_service(fake_client)

    response = client.post(
        f"/api/sessions/{session['id']}/feedback/llm",
        headers={"Authorization": f"Bearer {token}"},
    )
    app.dependency_overrides.pop(get_llm_feedback_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["fallback_used"] is False
    assert payload["enhanced_feedback_items"][0]["fallback_used"] is False
    assert "knees steady" in payload["enhanced_feedback_items"][0]["llm_coaching_cue"]
    assert "steady knee tracking" in payload["enhanced_summary"]["llm_summary"]


def test_phase3b_missing_key_falls_back_cleanly(client, db_session) -> None:
    token = _register_user(client, email="phase3b-no-key@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)
    _store_feedback_inputs(db_session, session_id=session["id"], drill=drill)
    fake_client = FakeLLMClient(fail=True)
    app.dependency_overrides[get_llm_feedback_service] = lambda: _llm_service(
        fake_client,
        config=_provider_config(enabled=True, api_key=None),
    )

    response = client.post(
        f"/api/sessions/{session['id']}/feedback/llm",
        headers={"Authorization": f"Bearer {token}"},
    )
    app.dependency_overrides.pop(get_llm_feedback_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["fallback_used"] is True
    assert payload["enhanced_feedback_items"][0]["fallback_used"] is True
    assert payload["enhanced_feedback_items"][0]["llm_coaching_cue"] == "Keep both knees tracking over the middle toes."
    assert "LLM_API_KEY_MISSING" in payload["diagnostic_flags"]
    assert "ADVANCED_CONTEXT_MISSING:ontology_reasoning_result" in payload["context_diagnostic_flags"]
    assert fake_client.calls == []


def test_phase3b_provider_failure_and_malformed_output_fall_back(client, db_session) -> None:
    token = _register_user(client, email="phase3b-failure@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)
    evaluation_result, feedback_result = _store_feedback_inputs(
        db_session,
        session_id=session["id"],
        drill=drill,
    )
    session_model = db_session.get(TrainingSession, UUID(session["id"]))

    failed_result = _llm_service(FakeLLMClient(fail=True)).enhance(
        session=session_model,
        evaluation_result=evaluation_result,
        feedback_result=feedback_result,
    )
    malformed_result = _llm_service(
        FakeLLMClient(responses=["   ", "   "])
    ).enhance(
        session=session_model,
        evaluation_result=evaluation_result,
        feedback_result=feedback_result,
    )

    assert failed_result.fallback_used is True
    assert failed_result.enhanced_feedback_items[0].fallback_used is True
    assert "LLM_ITEM_FALLBACK:knee_alignment_score" in failed_result.diagnostic_flags
    assert "LLM_SUMMARY_FALLBACK" in failed_result.diagnostic_flags
    assert malformed_result.fallback_used is True
    assert malformed_result.enhanced_feedback_items[0].fallback_used is True


def test_phase3b_internal_analysis_terms_fall_back(client, db_session) -> None:
    token = _register_user(client, email="phase3b-internal-term@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)
    evaluation_result, feedback_result = _store_feedback_inputs(
        db_session,
        session_id=session["id"],
        drill=drill,
    )
    session_model = db_session.get(TrainingSession, UUID(session["id"]))

    result = _llm_service(
        FakeLLMClient(
            responses=[
                (
                    "Main cue: Choquet says your knee control is linked.\n"
                    "Fix: Keep the knees steady.\n"
                    "Next session cue: Repeat one slower rep."
                ),
                "Keep the next rep slower and hold the knee line steady.",
            ]
        )
    ).enhance(
        session=session_model,
        evaluation_result=evaluation_result,
        feedback_result=feedback_result,
    )

    assert result.fallback_used is False
    assert result.enhanced_feedback_items[0].fallback_used is True
    assert result.enhanced_feedback_items[0].llm_coaching_cue == (
        "Keep both knees tracking over the middle toes."
    )
    assert result.enhanced_summary.fallback_used is False
    assert result.enhanced_summary.llm_summary == (
        "Keep the next rep slower and hold the knee line steady."
    )
    assert "LLM_ITEM_FALLBACK:knee_alignment_score" in result.diagnostic_flags


def test_phase3b_disabled_llm_keeps_phase3a_flow_working(client, db_session) -> None:
    token = _register_user(client, email="phase3b-disabled@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)
    _store_feedback_inputs(db_session, session_id=session["id"], drill=drill)
    app.dependency_overrides[get_llm_feedback_service] = lambda: _llm_service(
        FakeLLMClient(fail=True),
        config=_provider_config(enabled=False),
    )

    deterministic_response = client.post(
        f"/api/sessions/{session['id']}/feedback",
        headers={"Authorization": f"Bearer {token}"},
    )
    llm_response = client.post(
        f"/api/sessions/{session['id']}/feedback/llm",
        headers={"Authorization": f"Bearer {token}"},
    )
    app.dependency_overrides.pop(get_llm_feedback_service, None)

    assert deterministic_response.status_code == 200
    assert deterministic_response.json()["status"] == "COMPLETED"
    assert llm_response.status_code == 200
    assert llm_response.json()["fallback_used"] is True
    assert "LLM_ENHANCEMENT_DISABLED" in llm_response.json()["diagnostic_flags"]


def test_phase3b_missing_advanced_artifacts_do_not_break_llm_feedback(client, db_session) -> None:
    token = _register_user(client, email="phase3b-missing-advanced@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)
    _store_feedback_inputs(db_session, session_id=session["id"], drill=drill)
    fake_client = FakeLLMClient(
        responses=[
            (
                "Main cue: Keep your knees tracking over your toes on the way down.\n"
                "Fix: Slow the descent and focus on knee alignment.\n"
                "Next session cue: On the next set, repeat one controlled descent."
            ),
            "Your main focus is knee alignment during the descent.",
        ]
    )
    app.dependency_overrides[get_llm_feedback_service] = lambda: _llm_service(fake_client)

    response = client.post(
        f"/api/sessions/{session['id']}/feedback/llm",
        headers={"Authorization": f"Bearer {token}"},
    )
    app.dependency_overrides.pop(get_llm_feedback_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["fallback_used"] is False
    assert payload["advanced_context_used"] is False
    assert "ADVANCED_CONTEXT_MISSING:ontology_reasoning_result" in payload["context_diagnostic_flags"]
    assert len(payload["enhanced_feedback_items"]) == 1


def test_phase3b_advanced_artifacts_are_used_in_endpoint_context(client, db_session) -> None:
    token = _register_user(client, email="phase3b-route-advanced@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)
    _store_feedback_inputs(db_session, session_id=session["id"], drill=drill)
    _store_advanced_context_artifacts(db_session, session_id=session["id"], drill=drill)
    fake_client = FakeLLMClient(
        responses=[
            (
                "Main cue: During the descent, keep the knees tracking and slow the rushed movement.\n"
                "Fix: Repeat the drill with one clear focus on knee tracking.\n"
                "Next session cue: On the next set, slow the first half of the descent."
            ),
            "Your main issue is lower-body alignment, and the rushed descent makes it harder to stay controlled.",
        ]
    )
    app.dependency_overrides[get_llm_feedback_service] = lambda: _llm_service(fake_client)

    response = client.post(
        f"/api/sessions/{session['id']}/feedback/llm",
        headers={"Authorization": f"Bearer {token}"},
    )
    app.dependency_overrides.pop(get_llm_feedback_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["advanced_context_used"] is True
    assert payload["advanced_context_sources"] == [
        "fuzzy_interpretation_result",
        "it2_fuzzy_interpretation_result",
        "pedagogical_decision_result",
        "ontology_reasoning_result",
        "choquet_aggregation_result",
        "temporal_modeling_result",
    ]
    assert payload["context_diagnostic_flags"] == []


def test_phase3b_provider_failure_still_falls_back_with_advanced_artifacts(client, db_session) -> None:
    token = _register_user(client, email="phase3b-advanced-fallback@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)
    evaluation_result, feedback_result = _store_feedback_inputs(
        db_session,
        session_id=session["id"],
        drill=drill,
    )
    advanced_artifacts = _build_advanced_artifacts(
        session_id=session["id"],
        drill=drill,
    )
    session_model = db_session.get(TrainingSession, UUID(session["id"]))
    assert session_model is not None

    result = _llm_service(FakeLLMClient(fail=True)).enhance(
        session=session_model,
        evaluation_result=evaluation_result,
        feedback_result=feedback_result,
        fuzzy_result=advanced_artifacts["fuzzy_interpretation_result"],
        it2_fuzzy_result=advanced_artifacts["it2_fuzzy_interpretation_result"],
        pedagogical_result=advanced_artifacts["pedagogical_decision_result"],
        ontology_result=advanced_artifacts["ontology_reasoning_result"],
        choquet_result=advanced_artifacts["choquet_aggregation_result"],
        temporal_result=advanced_artifacts["temporal_modeling_result"],
    )

    assert result.fallback_used is True
    assert result.advanced_context_used is True
    assert result.enhanced_feedback_items[0].fallback_used is True
    assert result.enhanced_feedback_items[0].llm_coaching_cue == "Keep both knees tracking over the middle toes."
