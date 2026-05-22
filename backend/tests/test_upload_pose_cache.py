from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

from app.engines.perception_interface.perception_service import (
    POSE_MODEL_NAME,
    PREPROCESSING_VERSION,
)
from app.schemas.session import (
    PoseProcessingCacheKey,
    PoseProcessingMetadata,
    PoseSequenceResponse,
)
from app.services.session_service import SessionService


class _FakeArtifactRepository:
    def __init__(self, pose_sequence: PoseSequenceResponse | None) -> None:
        self._pose_sequence = pose_sequence

    def get_by_session_and_type(self, **_: object) -> object | None:
        if self._pose_sequence is None:
            return None
        return SimpleNamespace(
            payload_json=self._pose_sequence.model_dump(
                mode="json",
                exclude={"created_at"},
            )
        )


def _build_service(pose_sequence: PoseSequenceResponse | None) -> SessionService:
    return SessionService(
        db=None,
        sessions=None,
        artifacts=_FakeArtifactRepository(pose_sequence),
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


def _cache_key(*, file_hash: str = "abc123") -> PoseProcessingCacheKey:
    return PoseProcessingCacheKey(
        file_hash=file_hash,
        target_pose_fps=20.0,
        max_inference_width=720,
        preprocessing_version=PREPROCESSING_VERSION,
        pose_model=POSE_MODEL_NAME,
    )


def _pose_sequence(
    *,
    session_id: UUID,
    cache_key: PoseProcessingCacheKey,
) -> PoseSequenceResponse:
    return PoseSequenceResponse(
        session_id=session_id,
        pose_model=POSE_MODEL_NAME,
        preprocessing_version=PREPROCESSING_VERSION,
        frame_count=2,
        valid_frame_count=2,
        status="COMPLETED",
        diagnostic_flags=[],
        processing_metadata=PoseProcessingMetadata(
            original_fps=30.0,
            target_pose_fps=cache_key.target_pose_fps,
            sampling_stride=3,
            original_frame_count=6,
            processed_frame_count=2,
            valid_frame_count=2,
            original_width=1280,
            original_height=720,
            inference_width=720,
            inference_height=405,
            cache_key=cache_key,
            cache_hit=False,
            processing_time_ms=125.0,
        ),
        sequence_data=[],
    )


def test_pose_cache_reuses_same_session_file_and_settings() -> None:
    session_id = uuid4()
    cache_key = _cache_key()
    service = _build_service(
        _pose_sequence(
            session_id=session_id,
            cache_key=cache_key,
        )
    )

    cached = service._get_cached_pose_sequence(
        session_id=session_id,
        cache_key=cache_key,
    )

    assert cached is not None
    assert cached.frame_count == 2
    assert cached.processing_metadata is not None
    assert cached.processing_metadata.cache_hit is True
    assert cached.processing_metadata.cache_key == cache_key


def test_pose_cache_misses_when_file_hash_changes() -> None:
    session_id = uuid4()
    service = _build_service(
        _pose_sequence(
            session_id=session_id,
            cache_key=_cache_key(file_hash="old-file"),
        )
    )

    assert (
        service._get_cached_pose_sequence(
            session_id=session_id,
            cache_key=_cache_key(file_hash="new-file"),
        )
        is None
    )


def test_pose_cache_misses_when_processing_settings_change() -> None:
    session_id = uuid4()
    stored_cache_key = _cache_key()
    changed_cache_key = stored_cache_key.model_copy(
        update={
            "target_pose_fps": 8.0,
        }
    )
    service = _build_service(
        _pose_sequence(
            session_id=session_id,
            cache_key=stored_cache_key,
        )
    )

    assert (
        service._get_cached_pose_sequence(
            session_id=session_id,
            cache_key=changed_cache_key,
        )
        is None
    )
