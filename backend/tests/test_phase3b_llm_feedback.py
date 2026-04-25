from __future__ import annotations

import json
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
    DeterministicEvaluationIssueResponse,
    DeterministicEvaluationResult,
    DeterministicFeedbackResult,
    EvaluationFrameRangeResponse,
    MetricEvaluationResultResponse,
    PhaseEvaluationResultResponse,
    RankedMetricResponse,
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
    provider: str = "fake-provider",
    model: str = "fake-model",
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


def test_phase3b_provider_config_reads_settings() -> None:
    settings = Settings(
        llm_provider="local-compatible",
        llm_model="coach-small",
        llm_api_key="abc",
        llm_base_url="http://localhost:11434/v1",
        llm_timeout_seconds=3.5,
        llm_temperature=0.0,
        llm_max_tokens=220,
        llm_enable_enhancement=True,
    )

    config = LLMProviderConfig.from_settings(settings)

    assert config.provider == "local-compatible"
    assert config.model == "coach-small"
    assert config.api_key == "abc"
    assert config.base_url == "http://localhost:11434/v1"
    assert config.timeout_seconds == 3.5
    assert config.temperature == 0.0
    assert config.max_tokens == 220
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
    assert issue_context.deterministic_coaching_cue == "Keep your knees tracking over your toes."
    assert context.summary_context.top_issue is not None
    assert context.summary_context.strongest_area == "posture_accuracy in setup"


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
    assert "Keep your knees tracking over your toes." in prompt_text
    assert "raw_value" in prompt_text


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
            json.dumps(
                {
                    "coaching_cue": "During the squat descent, keep both knees tracking over your toes.",
                    "improvement_suggestion": "Slow the descent and press the knees outward before standing up.",
                    "grounding_fields_used": [
                        "drill_name",
                        "phase_id",
                        "metric_id",
                        "severity_level",
                        "deterministic_coaching_cue",
                    ],
                }
            ),
            json.dumps(
                {
                    "summary": (
                        "Your squat setup was steady, but the descent needs attention first. "
                        "Keep the knees tracking over the toes and slow the next rep."
                    ),
                    "grounding_fields_used": [
                        "top_issue",
                        "strongest_area",
                        "skill_level",
                    ],
                }
            ),
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
        "enhanced_feedback_items",
        "enhanced_summary",
        "diagnostic_flags",
        "created_at",
    }
    assert payload["llm_feedback_version"] == "phase3b_v0_1_0"
    assert payload["provider"] == "fake-provider"
    assert payload["model"] == "fake-model"
    assert payload["fallback_used"] is False
    item = payload["enhanced_feedback_items"][0]
    assert item["metric_id"] == "knee_alignment_score"
    assert item["deterministic_coaching_cue"] == "Keep your knees tracking over your toes."
    assert "squat descent" in item["llm_coaching_cue"]
    assert item["fallback_used"] is False

    artifact = db_session.scalar(
        select(SessionArtifact).where(
            SessionArtifact.session_id == session["id"],
            SessionArtifact.artifact_type == "llm_feedback_result",
        )
    )
    assert artifact is not None
    assert artifact.payload_json["provider"] == "fake-provider"
    assert len(fake_client.calls) == 2


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
    assert payload["enhanced_feedback_items"][0]["llm_coaching_cue"] == "Keep your knees tracking over your toes."
    assert "LLM_API_KEY_MISSING" in payload["diagnostic_flags"]
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
        FakeLLMClient(responses=["not-json", json.dumps({"summary": ""})])
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
