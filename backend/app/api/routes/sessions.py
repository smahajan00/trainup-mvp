from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.core.dependencies import get_current_user, get_session_service
from app.models.user import User
from app.schemas.session import (
    ChoquetAggregationResult,
    DeterministicEvaluationResult,
    DeterministicFeedbackResult,
    FrameBatchRequest,
    FrameBatchResponse,
    FuzzyInterpretationResult,
    IT2FuzzyInterpretationResult,
    LLMFeedbackResult,
    LiveEndRequest,
    LiveReadinessRequest,
    LiveStartResponse,
    OntologyReasoningResult,
    PedagogicalDecisionResult,
    SessionCreateRequest,
    SessionArtifactsResponse,
    SessionResponse,
    UploadProcessingResponse,
)
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreateRequest,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    return session_service.create_session(user_id=current_user.id, payload=payload)


@router.get("/recent", response_model=list[SessionResponse])
def list_recent_sessions(
    limit: int = Query(default=10, ge=1, le=25),
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> list[SessionResponse]:
    return session_service.list_recent_sessions(user_id=current_user.id, limit=limit)


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    return session_service.get_session(user_id=current_user.id, session_id=session_id)


@router.get(
    "/{session_id}/artifacts",
    response_model=SessionArtifactsResponse,
)
def get_session_artifacts(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> SessionArtifactsResponse:
    return session_service.get_session_artifacts(
        user_id=current_user.id,
        session_id=session_id,
    )


@router.post(
    "/{session_id}/evaluate",
    response_model=DeterministicEvaluationResult,
)
def evaluate_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> DeterministicEvaluationResult:
    return session_service.evaluate_session(
        user_id=current_user.id,
        session_id=session_id,
    )


@router.post(
    "/{session_id}/feedback",
    response_model=DeterministicFeedbackResult,
)
def generate_session_feedback(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> DeterministicFeedbackResult:
    return session_service.generate_feedback(
        user_id=current_user.id,
        session_id=session_id,
    )


@router.post(
    "/{session_id}/interpret/fuzzy",
    response_model=FuzzyInterpretationResult,
)
def generate_fuzzy_session_interpretation(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> FuzzyInterpretationResult:
    return session_service.generate_fuzzy_interpretation(
        user_id=current_user.id,
        session_id=session_id,
    )


@router.post(
    "/{session_id}/interpret/it2-fuzzy",
    response_model=IT2FuzzyInterpretationResult,
)
def generate_it2_fuzzy_session_interpretation(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> IT2FuzzyInterpretationResult:
    return session_service.generate_it2_fuzzy_interpretation(
        user_id=current_user.id,
        session_id=session_id,
    )


@router.post(
    "/{session_id}/pedagogy",
    response_model=PedagogicalDecisionResult,
)
def generate_session_pedagogy(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> PedagogicalDecisionResult:
    return session_service.generate_pedagogical_decision(
        user_id=current_user.id,
        session_id=session_id,
    )


@router.post(
    "/{session_id}/ontology",
    response_model=OntologyReasoningResult,
)
def generate_session_ontology_reasoning(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> OntologyReasoningResult:
    return session_service.generate_ontology_reasoning(
        user_id=current_user.id,
        session_id=session_id,
    )


@router.post(
    "/{session_id}/aggregate/choquet",
    response_model=ChoquetAggregationResult,
)
def generate_session_choquet_aggregation(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> ChoquetAggregationResult:
    return session_service.generate_choquet_aggregation(
        user_id=current_user.id,
        session_id=session_id,
    )


@router.post(
    "/{session_id}/feedback/llm",
    response_model=LLMFeedbackResult,
)
def generate_llm_session_feedback(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> LLMFeedbackResult:
    return session_service.generate_llm_feedback(
        user_id=current_user.id,
        session_id=session_id,
    )


@router.post(
    "/{session_id}/upload",
    response_model=UploadProcessingResponse,
    response_model_exclude_none=True,
)
def upload_session_media(
    session_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> UploadProcessingResponse:
    file_bytes = file.file.read()
    return session_service.process_upload(
        user_id=current_user.id,
        session_id=session_id,
        file_name=file.filename,
        content_type=file.content_type,
        file_size_bytes=len(file_bytes),
        file_bytes=file_bytes,
    )


@router.post("/{session_id}/live/start", response_model=LiveStartResponse)
def start_live_session(
    session_id: UUID,
    payload: LiveReadinessRequest,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> LiveStartResponse:
    return session_service.start_live_session(
        user_id=current_user.id,
        session_id=session_id,
        payload=payload,
    )


@router.post("/{session_id}/live/frame-batch", response_model=FrameBatchResponse)
def submit_frame_batch(
    session_id: UUID,
    payload: FrameBatchRequest,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> FrameBatchResponse:
    return session_service.accept_live_frame_batch(
        user_id=current_user.id,
        session_id=session_id,
        payload=payload,
    )


@router.post("/{session_id}/live/end", response_model=SessionResponse)
def end_live_session(
    session_id: UUID,
    payload: LiveEndRequest,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    return session_service.end_live_session(
        user_id=current_user.id,
        session_id=session_id,
        payload=payload,
    )
