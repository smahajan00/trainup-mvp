from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import TokenDecodeError, decode_access_token
from app.engines.perception_interface.perception_service import PerceptionService
from app.engines.cognition_engine.phase2a_evaluator import Phase2AEvaluator
from app.models.user import User
from app.repositories.drill_repository import DrillRepository
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.metric_result_repository import MetricResultRepository
from app.repositories.metric_type_repository import MetricTypeRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.progress_repository import ProgressRepository
from app.repositories.session_artifact_repository import SessionArtifactRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.session_summary_repository import SessionSummaryRepository
from app.repositories.sport_repository import SportRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.capture_protocol_validator import CaptureProtocolValidator
from app.services.deterministic_feedback_service import DeterministicFeedbackService
from app.services.dominant_side_detector import DominantSideDetector
from app.services.drill_service import DrillService
from app.services.fuzzy_interpretation_service import FuzzyInterpretationService
from app.services.it2_fuzzy_interpretation_service import IT2FuzzyInterpretationService
from app.services.choquet_aggregation_service import ChoquetAggregationService
from app.services.llm_client import LLMProviderConfig, OpenAICompatibleLLMClient
from app.services.llm_feedback_service import (
    CoachingContextBuilder,
    LLMFeedbackPromptBuilder,
    LLMFeedbackService,
)
from app.services.ontology_reasoning_service import OntologyReasoningService
from app.services.pedagogical_decision_service import PedagogicalDecisionService
from app.services.profile_service import ProfileService
from app.services.progress_service import ProgressService
from app.services.session_service import SessionService
from app.services.temporal_modeling_service import TemporalModelingService

bearer_scheme = HTTPBearer(auto_error=False)


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_profile_repository(db: Session = Depends(get_db)) -> ProfileRepository:
    return ProfileRepository(db)


def get_drill_repository(db: Session = Depends(get_db)) -> DrillRepository:
    return DrillRepository(db)


def get_sport_repository(db: Session = Depends(get_db)) -> SportRepository:
    return SportRepository(db)


def get_session_repository(db: Session = Depends(get_db)) -> SessionRepository:
    return SessionRepository(db)


def get_session_artifact_repository(
    db: Session = Depends(get_db),
) -> SessionArtifactRepository:
    return SessionArtifactRepository(db)


def get_feedback_repository(db: Session = Depends(get_db)) -> FeedbackRepository:
    return FeedbackRepository(db)


def get_metric_result_repository(db: Session = Depends(get_db)) -> MetricResultRepository:
    return MetricResultRepository(db)


def get_metric_type_repository(db: Session = Depends(get_db)) -> MetricTypeRepository:
    return MetricTypeRepository(db)


def get_session_summary_repository(
    db: Session = Depends(get_db),
) -> SessionSummaryRepository:
    return SessionSummaryRepository(db)


def get_progress_repository(db: Session = Depends(get_db)) -> ProgressRepository:
    return ProgressRepository(db)


def get_perception_service() -> PerceptionService:
    return PerceptionService()


def get_capture_protocol_validator() -> CaptureProtocolValidator:
    return CaptureProtocolValidator()


def get_phase2a_evaluator() -> Phase2AEvaluator:
    return Phase2AEvaluator()


def get_deterministic_feedback_service() -> DeterministicFeedbackService:
    return DeterministicFeedbackService()


def get_dominant_side_detector() -> DominantSideDetector:
    return DominantSideDetector()


def get_fuzzy_interpretation_service() -> FuzzyInterpretationService:
    return FuzzyInterpretationService(enabled=settings.fuzzy_interpretation_enabled)


def get_it2_fuzzy_interpretation_service() -> IT2FuzzyInterpretationService:
    return IT2FuzzyInterpretationService(enabled=settings.it2_fuzzy_enabled)


def get_pedagogical_decision_service() -> PedagogicalDecisionService:
    return PedagogicalDecisionService()


def get_ontology_reasoning_service() -> OntologyReasoningService:
    return OntologyReasoningService()


def get_choquet_aggregation_service() -> ChoquetAggregationService:
    return ChoquetAggregationService()


def get_temporal_modeling_service() -> TemporalModelingService:
    return TemporalModelingService()


def get_llm_feedback_service() -> LLMFeedbackService:
    return LLMFeedbackService(
        llm_client=OpenAICompatibleLLMClient(),
        provider_config=LLMProviderConfig.from_settings(settings),
        context_builder=CoachingContextBuilder(),
        prompt_builder=LLMFeedbackPromptBuilder(),
    )


def get_auth_service(
    db: Session = Depends(get_db),
    users: UserRepository = Depends(get_user_repository),
) -> AuthService:
    return AuthService(db=db, users=users)


def get_profile_service(
    db: Session = Depends(get_db),
    profiles: ProfileRepository = Depends(get_profile_repository),
    sports: SportRepository = Depends(get_sport_repository),
) -> ProfileService:
    return ProfileService(db=db, profiles=profiles, sports=sports)


def get_drill_service(
    drills: DrillRepository = Depends(get_drill_repository),
    sports: SportRepository = Depends(get_sport_repository),
) -> DrillService:
    return DrillService(drills=drills, sports=sports)


def get_progress_service(
    summaries: SessionSummaryRepository = Depends(get_session_summary_repository),
    progress_records: ProgressRepository = Depends(get_progress_repository),
) -> ProgressService:
    return ProgressService(summaries=summaries, progress_records=progress_records)


def get_session_service(
    db: Session = Depends(get_db),
    sessions: SessionRepository = Depends(get_session_repository),
    artifacts: SessionArtifactRepository = Depends(get_session_artifact_repository),
    feedback: FeedbackRepository = Depends(get_feedback_repository),
    metric_types: MetricTypeRepository = Depends(get_metric_type_repository),
    metric_results: MetricResultRepository = Depends(get_metric_result_repository),
    summaries: SessionSummaryRepository = Depends(get_session_summary_repository),
    progress_records: ProgressRepository = Depends(get_progress_repository),
    drills: DrillRepository = Depends(get_drill_repository),
    perception: PerceptionService = Depends(get_perception_service),
    capture_protocol: CaptureProtocolValidator = Depends(get_capture_protocol_validator),
    phase2a_evaluator: Phase2AEvaluator = Depends(get_phase2a_evaluator),
    dominant_side_detector: DominantSideDetector = Depends(get_dominant_side_detector),
    deterministic_feedback: DeterministicFeedbackService = Depends(
        get_deterministic_feedback_service
    ),
    fuzzy_interpretation: FuzzyInterpretationService = Depends(
        get_fuzzy_interpretation_service
    ),
    it2_fuzzy_interpretation: IT2FuzzyInterpretationService = Depends(
        get_it2_fuzzy_interpretation_service
    ),
    llm_feedback: LLMFeedbackService = Depends(get_llm_feedback_service),
    pedagogical_decision: PedagogicalDecisionService = Depends(
        get_pedagogical_decision_service
    ),
    ontology_reasoning: OntologyReasoningService = Depends(
        get_ontology_reasoning_service
    ),
    choquet_aggregation: ChoquetAggregationService = Depends(
        get_choquet_aggregation_service
    ),
    temporal_modeling: TemporalModelingService = Depends(get_temporal_modeling_service),
) -> SessionService:
    return SessionService(
        db=db,
        sessions=sessions,
        artifacts=artifacts,
        feedback=feedback,
        metric_types=metric_types,
        metric_results=metric_results,
        summaries=summaries,
        progress_records=progress_records,
        drills=drills,
        perception=perception,
        capture_protocol=capture_protocol,
        phase2a_evaluator=phase2a_evaluator,
        dominant_side_detector=dominant_side_detector,
        deterministic_feedback=deterministic_feedback,
        fuzzy_interpretation=fuzzy_interpretation,
        it2_fuzzy_interpretation=it2_fuzzy_interpretation,
        llm_feedback=llm_feedback,
        pedagogical_decision=pedagogical_decision,
        ontology_reasoning=ontology_reasoning,
        choquet_aggregation=choquet_aggregation,
        temporal_modeling=temporal_modeling,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    users: UserRepository = Depends(get_user_repository),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(str(payload["sub"]))
    except (TokenDecodeError, ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = users.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user was not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
