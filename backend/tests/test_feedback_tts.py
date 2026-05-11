from __future__ import annotations

import io
from types import SimpleNamespace
from uuid import UUID, uuid4

import numpy as np
import soundfile as sf

from app.schemas.session import (
    DeterministicFeedbackItemResponse,
    DeterministicFeedbackResult,
    LLMEnhancedFeedbackItemResponse,
    LLMEnhancedSessionSummaryResponse,
    LLMFeedbackResult,
)
from app.services.feedback_tts_service import KOKORO_SAMPLE_RATE, KokoroFeedbackTTSService
from app.services.session_service import SessionService


class _FakeArtifactRepository:
    def __init__(
        self,
        feedback_result: DeterministicFeedbackResult | None,
        llm_result: LLMFeedbackResult | None = None,
    ) -> None:
        self._feedback_result = feedback_result
        self._llm_result = llm_result

    def get_by_session_and_type(self, **_: object) -> object | None:
        artifact_type = _.get("artifact_type")
        payload = None
        if artifact_type == "feedback_result":
            payload = self._feedback_result
        elif artifact_type == "llm_feedback_result":
            payload = self._llm_result

        if payload is None:
            return None
        return SimpleNamespace(
            payload_json=payload.model_dump(
                mode="json",
                exclude={"created_at"},
            )
        )


def _build_service(
    feedback_result: DeterministicFeedbackResult | None,
    llm_result: LLMFeedbackResult | None = None,
) -> SessionService:
    return SessionService(
        db=None,
        sessions=None,
        artifacts=_FakeArtifactRepository(feedback_result, llm_result),
        feedback=None,
        metric_types=None,
        metric_results=None,
        summaries=None,
        progress_records=None,
        drills=None,
        perception=None,
        capture_protocol=None,
        phase2a_evaluator=None,
        dominant_side_detector=None,
        deterministic_feedback=None,
        fuzzy_interpretation=None,
        it2_fuzzy_interpretation=None,
        llm_feedback=None,
        feedback_tts=None,
        pedagogical_decision=None,
        ontology_reasoning=None,
        choquet_aggregation=None,
        temporal_modeling=None,
    )


def _feedback_item(
    *,
    phase_id: str,
    metric_name: str,
    priority_rank: int,
    simple_coaching_phrase: str,
) -> DeterministicFeedbackItemResponse:
    return DeterministicFeedbackItemResponse(
        phase_id=phase_id,
        metric_id=f"{metric_name}_id",
        metric_name=metric_name,
        severity_level="MODERATE",
        affected_body_part="lower_body",
        issue_direction="UNDER_RANGE",
        issue_title=f"Improve {metric_name}",
        coaching_cue=f"Control {metric_name}.",
        improvement_suggestion=f"Repeat {metric_name} with control.",
        what_happened=f"{metric_name} drifted during the rep.",
        why_it_matters=f"{metric_name} affects movement quality.",
        what_to_fix=f"Keep {metric_name} steady.",
        next_rep_cue=f"Next rep, set {metric_name} early.",
        simple_coaching_phrase=simple_coaching_phrase,
        priority_rank=priority_rank,
        deviation=0.25,
    )


def _feedback_result(session_id: UUID) -> DeterministicFeedbackResult:
    return DeterministicFeedbackResult(
        status="COMPLETED",
        session_id=session_id,
        overall_feedback_summary="Keep one clean correction for the next rep.",
        prioritized_feedback_items=[
            _feedback_item(
                phase_id="setup",
                metric_name="balance",
                priority_rank=1,
                simple_coaching_phrase="Hold balance first.",
            ),
            _feedback_item(
                phase_id="release",
                metric_name="knee_load",
                priority_rank=2,
                simple_coaching_phrase="Control the knee load.",
            ),
        ],
        improvement_suggestions=["Repeat the correction for three reps."],
        diagnostic_flags=[],
    )


def _llm_result(session_id: UUID) -> LLMFeedbackResult:
    return LLMFeedbackResult(
        session_id=session_id,
        provider="llama_cpp",
        model="Qwen2.5-7B-Instruct-Q4_K_M.gguf",
        fallback_used=False,
        advanced_context_used=True,
        advanced_context_sources=["fuzzy_interpretation_result"],
        enhanced_feedback_items=[
            LLMEnhancedFeedbackItemResponse(
                phase_id="release",
                metric_id="knee_load_id",
                metric_name="knee_load",
                severity_level="MODERATE",
                priority_rank=2,
                affected_body_part="lower_body",
                issue_direction="UNDER_RANGE",
                deterministic_coaching_cue="Control knee_load.",
                llm_coaching_cue="Keep the knee load smooth through the release.",
                deterministic_improvement_suggestion="Repeat knee_load with control.",
                llm_improvement_suggestion="Next session, slow the setup and repeat the same knee line.",
                grounding_fields_used=["metric_name", "deterministic_coaching_cue"],
                fallback_used=False,
            )
        ],
        enhanced_summary=LLMEnhancedSessionSummaryResponse(
            deterministic_summary="Keep one clean correction for the next rep.",
            llm_summary="Keep the knee line smooth and controlled.",
            grounding_fields_used=["top_issue"],
            fallback_used=False,
        ),
        diagnostic_flags=[],
    )


def test_feedback_tts_segments_use_selected_feedback_item() -> None:
    session_id = uuid4()
    service = _build_service(_feedback_result(session_id))

    segments = service._build_tts_segments_from_feedback(
        session_id=session_id,
        feedback_item_key="release:knee_load:2",
    )

    assert segments.segment_1 == "Control the knee load."
    assert segments.segment_2 == "Keep knee load steady."
    assert segments.segment_3 == "Next rep, set knee load early."


def test_feedback_tts_segments_prefer_final_llm_text_when_available() -> None:
    session_id = uuid4()
    service = _build_service(_feedback_result(session_id), _llm_result(session_id))

    segments = service._build_tts_segments_from_feedback(
        session_id=session_id,
        feedback_item_key="release:knee_load:2",
    )

    assert segments.segment_1 == "Keep the knee load smooth through the release."
    assert segments.segment_2 == "Keep knee load steady."
    assert segments.segment_3 == (
        "Next session, slow the setup and repeat the same knee line."
    )


def test_feedback_tts_segments_default_to_top_priority_item() -> None:
    session_id = uuid4()
    service = _build_service(_feedback_result(session_id))

    segments = service._build_tts_segments_from_feedback(
        session_id=session_id,
        feedback_item_key=None,
    )

    assert segments.segment_1 == "Hold balance first."
    assert segments.segment_2 == "Keep balance steady."
    assert segments.segment_3 == "Next rep, set balance early."


def test_feedback_tts_text_normalization_removes_diagnostics() -> None:
    cleaned = KokoroFeedbackTTSService.normalize_text_segment(
        "MISSING_FEEDBACK_RESULT knee_tracking TORSO_CONTROL "
        "Priority 1 item selected for intermediate coaching emphasis."
    )

    assert cleaned == "knee tracking torso control"


class _FakeKokoroPipeline:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def __call__(self, text: str, *, voice: str):
        self.texts.append(text)
        yield None, None, np.ones(240, dtype=np.float32)


def test_feedback_tts_inserts_silence_between_segments() -> None:
    fake_pipeline = _FakeKokoroPipeline()
    service = KokoroFeedbackTTSService(pause_ms=400)
    object.__setattr__(service, "_pipeline", fake_pipeline)

    audio_bytes = service.synthesize(
        segments=["Main cue.", "What to fix.", "Next session cue."]
    )

    audio, sample_rate = sf.read(io.BytesIO(audio_bytes), dtype="float32")
    expected_pause_samples = int(KOKORO_SAMPLE_RATE * 0.4)
    expected_samples = (3 * 240) + (2 * expected_pause_samples)

    assert sample_rate == KOKORO_SAMPLE_RATE
    assert len(audio) == expected_samples
    assert np.allclose(audio[240 : 240 + expected_pause_samples], 0)
    assert fake_pipeline.texts == ["Main cue.", "What to fix.", "Next session cue."]
