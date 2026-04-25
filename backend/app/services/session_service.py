from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.engines.cognition_engine.phase2a_evaluator import Phase2AEvaluator
from app.engines.cognition_engine.phase2a_contract import (
    PHASE2A_EVALUATION_VERSION,
    get_phase2a_contract,
)
from app.engines.perception_interface.perception_service import PerceptionService
from app.models.drill import Drill
from app.models.enums import CameraView, InputType, SessionStatus, SeverityLevel
from app.models.metric_type import MetricType
from app.models.training_session import TrainingSession
from app.repositories.drill_repository import DrillRepository
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.metric_result_repository import MetricResultRepository
from app.repositories.metric_type_repository import MetricTypeRepository
from app.repositories.progress_repository import ProgressRepository
from app.repositories.session_artifact_repository import SessionArtifactRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.session_summary_repository import SessionSummaryRepository
from app.schemas.progress import SessionSummaryResponse
from app.schemas.session import (
    ChoquetAggregationResult,
    CognitionResult,
    DeterministicEvaluationResult,
    DeterministicFeedbackItemResponse,
    DeterministicFeedbackResult,
    FeedbackResponse,
    FrameBatchRequest,
    FrameBatchResponse,
    FuzzyInterpretationResult,
    IT2FuzzyInterpretationResult,
    LLMFeedbackResult,
    LiveEndRequest,
    LiveReadinessRequest,
    LiveStartResponse,
    MetricEvaluationResultResponse,
    OntologyReasoningResult,
    PedagogicalDecisionResult,
    PerceptionResult,
    PoseSequenceResponse,
    PoseSequenceSummaryResponse,
    SessionCreateRequest,
    SessionArtifactsResponse,
    SessionArtifactResponse,
    SessionResponse,
    TemporalModelingResult,
    UploadProcessingResponse,
)
from app.services.capture_protocol_validator import CaptureProtocolValidator
from app.services.deterministic_feedback_service import DeterministicFeedbackService
from app.services.fuzzy_interpretation_service import FuzzyInterpretationService
from app.services.it2_fuzzy_interpretation_service import IT2FuzzyInterpretationService
from app.services.llm_feedback_service import LLMFeedbackService
from app.services.choquet_aggregation_service import ChoquetAggregationService
from app.services.ontology_reasoning_service import OntologyReasoningService
from app.services.pedagogical_decision_service import PedagogicalDecisionService
from app.services.temporal_modeling_service import TemporalModelingService
from app.models.session_summary import SessionSummary

PERCEPTION_ARTIFACT_TYPE = "perception_payload"
COGNITION_ARTIFACT_TYPE = "cognition_result"
EVALUATION_ARTIFACT_TYPE = "evaluation_result"
FEEDBACK_ARTIFACT_TYPE = "feedback_result"
LLM_FEEDBACK_ARTIFACT_TYPE = "llm_feedback_result"
FUZZY_INTERPRETATION_ARTIFACT_TYPE = "fuzzy_interpretation_result"
IT2_FUZZY_INTERPRETATION_ARTIFACT_TYPE = "it2_fuzzy_interpretation_result"
PEDAGOGICAL_ARTIFACT_TYPE = "pedagogical_decision_result"
ONTOLOGY_REASONING_ARTIFACT_TYPE = "ontology_reasoning_result"
CHOQUET_AGGREGATION_ARTIFACT_TYPE = "choquet_aggregation_result"
TEMPORAL_MODELING_ARTIFACT_TYPE = "temporal_modeling_result"
POSE_SEQUENCE_ARTIFACT_TYPE = "pose_sequence"
logger = logging.getLogger(__name__)

SAGITTAL_LANDMARK_SWAP_PAIRS = (
    ("left_shoulder", "right_shoulder"),
    ("left_elbow", "right_elbow"),
    ("left_wrist", "right_wrist"),
    ("left_hip", "right_hip"),
    ("left_knee", "right_knee"),
    ("left_ankle", "right_ankle"),
    ("left_heel", "right_heel"),
    ("left_foot_index", "right_foot_index"),
)


def normalize_pose_sequence_for_camera_view(
    *,
    pose_sequence: PoseSequenceResponse,
    camera_view: CameraView | None,
) -> PoseSequenceResponse:
    if camera_view is not CameraView.LEFT_SAGITTAL:
        return pose_sequence

    normalized_frames = []
    for frame in pose_sequence.sequence_data:
        landmarks = dict(frame.landmarks)
        for left_name, right_name in SAGITTAL_LANDMARK_SWAP_PAIRS:
            left_landmark = landmarks.get(left_name)
            right_landmark = landmarks.get(right_name)
            if right_landmark is not None:
                landmarks[left_name] = right_landmark
            elif left_name in landmarks:
                del landmarks[left_name]
            if left_landmark is not None:
                landmarks[right_name] = left_landmark
            elif right_name in landmarks:
                del landmarks[right_name]

        normalized_frames.append(frame.model_copy(update={"landmarks": landmarks}))

    return pose_sequence.model_copy(update={"sequence_data": normalized_frames})


@dataclass
class SessionService:
    db: Session
    sessions: SessionRepository
    artifacts: SessionArtifactRepository
    feedback: FeedbackRepository
    metric_types: MetricTypeRepository
    metric_results: MetricResultRepository
    summaries: SessionSummaryRepository
    progress_records: ProgressRepository
    drills: DrillRepository
    perception: PerceptionService
    capture_protocol: CaptureProtocolValidator
    phase2a_evaluator: Phase2AEvaluator
    deterministic_feedback: DeterministicFeedbackService
    fuzzy_interpretation: FuzzyInterpretationService
    it2_fuzzy_interpretation: IT2FuzzyInterpretationService
    llm_feedback: LLMFeedbackService
    pedagogical_decision: PedagogicalDecisionService
    ontology_reasoning: OntologyReasoningService
    choquet_aggregation: ChoquetAggregationService
    temporal_modeling: TemporalModelingService

    def create_session(self, *, user_id: UUID, payload: SessionCreateRequest) -> SessionResponse:
        drill = self.drills.get_by_id(payload.drill_id)
        if drill is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requested drill was not found.",
            )

        self._ensure_sport_matches_drill(drill=drill, sport_id=payload.sport_id)
        self._ensure_dominant_side_requirement(
            drill=drill,
            payload=payload,
        )

        session = self.sessions.create(
            user_id=user_id,
            drill_id=payload.drill_id,
            input_type=payload.input_type,
            skill_level=payload.skill_level,
            camera_view=payload.camera_view,
            dominant_side=payload.dominant_side,
            status=SessionStatus.ACTIVE,
            start_time=datetime.now(UTC),
        )
        self.db.commit()
        return self._build_session_response(session)

    def get_session(self, *, user_id: UUID, session_id: UUID) -> SessionResponse:
        session = self._get_owned_session(user_id=user_id, session_id=session_id)
        return self._build_session_response(session)

    def list_recent_sessions(self, *, user_id: UUID, limit: int = 10) -> list[SessionResponse]:
        return [
            self._build_session_response(session)
            for session in self.sessions.list_recent_for_user(user_id=user_id, limit=limit)
        ]

    def process_upload(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        file_name: str | None,
        content_type: str | None,
        file_size_bytes: int,
        file_bytes: bytes,
    ) -> UploadProcessingResponse:
        session = self._get_owned_session(user_id=user_id, session_id=session_id)
        self._ensure_input_type(session, InputType.UPLOAD)
        self._ensure_session_open(session)

        logger.info(
            "Starting upload session processing",
            extra={
                "session_id": str(session.id),
                "user_id": str(user_id),
                "drill_id": str(session.drill_id),
            },
        )

        try:
            capture_validation = self.capture_protocol.validate(
                drill=session.drill,
                actual_view=session.camera_view,
            )
            validation = self.perception.validate_upload(
                file_name=file_name,
                content_type=content_type,
                file_size_bytes=file_size_bytes,
            )
            if not capture_validation.is_valid:
                logger.warning(
                    "Capture protocol validation failed",
                    extra={
                        "session_id": str(session.id),
                        "reason_code": capture_validation.reason_code,
                        "expected_view": (
                            capture_validation.expected_view.value
                            if capture_validation.expected_view is not None
                            else None
                        ),
                        "actual_view": (
                            capture_validation.actual_view.value
                            if capture_validation.actual_view is not None
                            else None
                        ),
                    },
                )
                return UploadProcessingResponse(
                    session_id=session.id,
                    status=session.status,
                    upload_received=False,
                    validation=validation,
                    capture_validation=capture_validation,
                    next_step="Update the capture view configuration and try again.",
                )
            if not validation.is_valid:
                logger.warning(
                    "Upload validation failed",
                    extra={
                        "session_id": str(session.id),
                        "errors": validation.errors,
                        "warnings": validation.warnings,
                    },
                )
                return UploadProcessingResponse(
                    session_id=session.id,
                    status=session.status,
                    upload_received=False,
                    validation=validation,
                    capture_validation=capture_validation,
                    next_step="Fix the file issues and try again.",
                )

            tracked_joints = self._resolve_tracked_joints(session)
            pose_sequence = self.perception.process_uploaded_file(
                session_id=session.id,
                drill_id=session.drill_id,
                file_name=file_name or "uploaded-video",
                content_type=validation.content_type or "application/octet-stream",
                file_size_bytes=file_size_bytes,
                tracked_joints=tracked_joints,
                file_bytes=file_bytes,
            )
            pose_sequence_artifact = self.artifacts.upsert(
                session_id=session.id,
                artifact_type=POSE_SEQUENCE_ARTIFACT_TYPE,
                payload_json=pose_sequence.model_dump(
                    mode="json",
                    exclude={"created_at"},
                ),
            )
            self._clear_phase0_outputs(session_id=session.id)
            self.db.commit()
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            logger.exception(
                "Upload session processing failed",
                extra={
                    "session_id": str(session.id),
                    "user_id": str(user_id),
                    "drill_id": str(session.drill_id),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Processing failed. Please retry the upload.",
            ) from exc

        logger.info(
            "Upload session processing completed",
            extra={
                "session_id": str(session.id),
                "pose_status": pose_sequence.status,
                "valid_frame_count": pose_sequence.valid_frame_count,
            },
        )

        return UploadProcessingResponse(
            session_id=session.id,
            status=session.status,
            upload_received=True,
            validation=validation,
            capture_validation=capture_validation,
            pose_sequence=self._build_pose_sequence_summary_response(
                pose_sequence=pose_sequence,
            ),
            feedback=[],
            artifacts_persisted=[
                pose_sequence_artifact.artifact_type,
            ],
            next_step=self._build_next_step(pose_sequence=pose_sequence),
        )

    def get_session_artifacts(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
    ) -> SessionArtifactsResponse:
        session = self._get_owned_session(user_id=user_id, session_id=session_id)
        artifacts = self.artifacts.list_by_session_id(session_id=session.id)
        feedback_rows = self.feedback.list_by_session_id(session_id=session.id)
        session_summary = self.summaries.get_by_session_id(session_id=session.id)

        pose_sequence: PoseSequenceResponse | None = None
        perception_result = None
        cognition_result = None
        evaluation_result = None
        feedback_result = None
        llm_feedback_result = None
        fuzzy_interpretation_result = None
        it2_fuzzy_interpretation_result = None
        pedagogical_decision_result = None
        ontology_reasoning_result = None
        choquet_aggregation_result = None
        temporal_modeling_result = None

        for artifact in artifacts:
            if artifact.artifact_type == POSE_SEQUENCE_ARTIFACT_TYPE:
                pose_sequence = PoseSequenceResponse(
                    **artifact.payload_json,
                    created_at=artifact.created_at,
                )
            elif artifact.artifact_type == PERCEPTION_ARTIFACT_TYPE:
                perception_result = PerceptionResult(**artifact.payload_json)
            elif artifact.artifact_type == COGNITION_ARTIFACT_TYPE:
                cognition_result = CognitionResult(**artifact.payload_json)
            elif artifact.artifact_type == EVALUATION_ARTIFACT_TYPE:
                evaluation_result = DeterministicEvaluationResult(**artifact.payload_json)
            elif artifact.artifact_type == FEEDBACK_ARTIFACT_TYPE:
                feedback_result = DeterministicFeedbackResult(**artifact.payload_json)
            elif artifact.artifact_type == LLM_FEEDBACK_ARTIFACT_TYPE:
                llm_feedback_result = LLMFeedbackResult(**artifact.payload_json)
            elif artifact.artifact_type == FUZZY_INTERPRETATION_ARTIFACT_TYPE:
                fuzzy_interpretation_result = FuzzyInterpretationResult(
                    **artifact.payload_json
                )
            elif artifact.artifact_type == IT2_FUZZY_INTERPRETATION_ARTIFACT_TYPE:
                it2_fuzzy_interpretation_result = IT2FuzzyInterpretationResult(
                    **artifact.payload_json
                )
            elif artifact.artifact_type == PEDAGOGICAL_ARTIFACT_TYPE:
                pedagogical_decision_result = PedagogicalDecisionResult(
                    **artifact.payload_json
                )
            elif artifact.artifact_type == ONTOLOGY_REASONING_ARTIFACT_TYPE:
                ontology_reasoning_result = OntologyReasoningResult(
                    **artifact.payload_json
                )
            elif artifact.artifact_type == CHOQUET_AGGREGATION_ARTIFACT_TYPE:
                choquet_aggregation_result = ChoquetAggregationResult(
                    **artifact.payload_json
                )
            elif artifact.artifact_type == TEMPORAL_MODELING_ARTIFACT_TYPE:
                temporal_modeling_result = TemporalModelingResult(
                    **artifact.payload_json
                )

        return SessionArtifactsResponse(
            artifacts=[
                SessionArtifactResponse(
                    id=artifact.id,
                    session_id=artifact.session_id,
                    artifact_type=artifact.artifact_type,
                    payload_json=artifact.payload_json,
                    created_at=artifact.created_at,
                )
                for artifact in artifacts
            ],
            pose_sequence=pose_sequence,
            perception_result=perception_result,
            cognition_result=cognition_result,
            evaluation_result=evaluation_result,
            feedback_result=feedback_result,
            llm_feedback_result=llm_feedback_result,
            fuzzy_interpretation_result=fuzzy_interpretation_result,
            it2_fuzzy_interpretation_result=it2_fuzzy_interpretation_result,
            pedagogical_decision_result=pedagogical_decision_result,
            ontology_reasoning_result=ontology_reasoning_result,
            choquet_aggregation_result=choquet_aggregation_result,
            temporal_modeling_result=temporal_modeling_result,
            session_summary=(
                self._build_session_summary_response(session_summary)
                if session_summary is not None
                else None
            ),
            feedback=[self._build_feedback_response(row) for row in feedback_rows],
        )

    def evaluate_session(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
    ) -> DeterministicEvaluationResult:
        session = self._get_owned_session(user_id=user_id, session_id=session_id)
        pose_artifact = self.artifacts.get_by_session_and_type(
            session_id=session.id,
            artifact_type=POSE_SEQUENCE_ARTIFACT_TYPE,
        )
        if pose_artifact is None:
            result = self._build_evaluation_failure(
                session=session,
                diagnostic_flags=["MISSING_POSE_SEQUENCE"],
            )
            self._persist_evaluation_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        try:
            pose_sequence = PoseSequenceResponse(**pose_artifact.payload_json)
        except Exception:
            result = self._build_evaluation_failure(
                session=session,
                diagnostic_flags=["MALFORMED_POSE_SEQUENCE"],
            )
            self._replace_metric_results(session_id=session.id, metric_results=[])
            self._persist_evaluation_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        if (
            pose_sequence.status != "COMPLETED"
            or pose_sequence.frame_count <= 0
            or pose_sequence.valid_frame_count <= 0
        ):
            result = self._build_evaluation_failure(
                session=session,
                diagnostic_flags=[
                    "UNUSABLE_POSE_SEQUENCE",
                    f"POSE_SEQUENCE_STATUS:{pose_sequence.status}",
                ],
                result_status=(
                    "INSUFFICIENT_DATA"
                    if pose_sequence.frame_count > 0
                    else "FAILED"
                ),
            )
            self._replace_metric_results(session_id=session.id, metric_results=[])
            self._persist_evaluation_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        evaluation_pose_sequence = normalize_pose_sequence_for_camera_view(
            pose_sequence=pose_sequence,
            camera_view=session.camera_view,
        )
        computation = self.phase2a_evaluator.evaluate(
            session=session,
            pose_sequence=evaluation_pose_sequence,
        )
        metric_names = {
            metric_result.metric_name
            for metric_result in computation.metric_results
        }
        metric_types_by_name = {
            metric.metric_name: metric
            for metric in self.metric_types.list_by_names(metric_names)
        }
        missing_metric_names = sorted(metric_names - set(metric_types_by_name.keys()))
        if missing_metric_names:
            result = self._build_evaluation_failure(
                session=session,
                diagnostic_flags=[
                    "MISSING_METRIC_TYPES",
                    *[f"MISSING_METRIC_TYPE:{name}" for name in missing_metric_names],
                ],
            )
            self._replace_metric_results(session_id=session.id, metric_results=[])
            self._persist_evaluation_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        self._replace_metric_results(
            session_id=session.id,
            metric_results=computation.metric_results,
            metric_types_by_name=metric_types_by_name,
        )
        self._persist_evaluation_result(session_id=session.id, result=computation.result)
        self.db.commit()
        return computation.result

    def generate_fuzzy_interpretation(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
    ) -> FuzzyInterpretationResult:
        session = self._get_owned_session(user_id=user_id, session_id=session_id)
        evaluation_result = self._load_evaluation_result_for_feedback(session=session)
        result = self.fuzzy_interpretation.interpret(
            evaluation_result=evaluation_result,
        )
        self._persist_fuzzy_interpretation_result(
            session_id=session.id,
            result=result,
        )
        self.db.commit()
        return result

    def generate_it2_fuzzy_interpretation(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
    ) -> IT2FuzzyInterpretationResult:
        session = self._get_owned_session(user_id=user_id, session_id=session_id)
        if not self.it2_fuzzy_interpretation.enabled:
            result = self.it2_fuzzy_interpretation.build_failure_result(
                session_id=session.id,
                sport_id=session.drill.sport_id,
                drill_id=session.drill_id,
                skill_level=session.skill_level,
                diagnostic_flags=["IT2_FUZZY_DISABLED"],
                status="DISABLED",
            )
            self._persist_it2_fuzzy_interpretation_result(
                session_id=session.id,
                result=result,
            )
            self.db.commit()
            return result

        fuzzy_artifact = self.artifacts.get_by_session_and_type(
            session_id=session.id,
            artifact_type=FUZZY_INTERPRETATION_ARTIFACT_TYPE,
        )
        if fuzzy_artifact is None:
            result = self.it2_fuzzy_interpretation.build_failure_result(
                session_id=session.id,
                sport_id=session.drill.sport_id,
                drill_id=session.drill_id,
                skill_level=session.skill_level,
                diagnostic_flags=["MISSING_FUZZY_INTERPRETATION_RESULT"],
            )
            self._persist_it2_fuzzy_interpretation_result(
                session_id=session.id,
                result=result,
            )
            self.db.commit()
            return result

        try:
            fuzzy_result = FuzzyInterpretationResult(**fuzzy_artifact.payload_json)
        except Exception:
            result = self.it2_fuzzy_interpretation.build_failure_result(
                session_id=session.id,
                sport_id=session.drill.sport_id,
                drill_id=session.drill_id,
                skill_level=session.skill_level,
                diagnostic_flags=["MALFORMED_FUZZY_INTERPRETATION_RESULT"],
            )
            self._persist_it2_fuzzy_interpretation_result(
                session_id=session.id,
                result=result,
            )
            self.db.commit()
            return result

        result = self.it2_fuzzy_interpretation.interpret(fuzzy_result=fuzzy_result)
        self._persist_it2_fuzzy_interpretation_result(
            session_id=session.id,
            result=result,
        )
        self.db.commit()
        return result

    def generate_feedback(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
    ) -> DeterministicFeedbackResult:
        session = self._get_owned_session(user_id=user_id, session_id=session_id)
        evaluation_artifact = self.artifacts.get_by_session_and_type(
            session_id=session.id,
            artifact_type=EVALUATION_ARTIFACT_TYPE,
        )
        if evaluation_artifact is None:
            result = self._build_feedback_failure(
                session=session,
                diagnostic_flags=["MISSING_EVALUATION_RESULT"],
                summary="Feedback could not be generated because no evaluation result exists.",
            )
            self._replace_feedback_outputs(session_id=session.id, result=result)
            self.db.commit()
            return result

        try:
            evaluation_result = DeterministicEvaluationResult(
                **evaluation_artifact.payload_json
            )
        except Exception:
            result = self._build_feedback_failure(
                session=session,
                diagnostic_flags=["MALFORMED_EVALUATION_RESULT"],
                summary="Feedback could not be generated because the evaluation result is malformed.",
            )
            self._replace_feedback_outputs(session_id=session.id, result=result)
            self.db.commit()
            return result

        result = self.deterministic_feedback.generate(
            evaluation_result=evaluation_result,
        )
        self._replace_feedback_outputs(session_id=session.id, result=result)
        self.db.commit()
        return result

    def generate_pedagogical_decision(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
    ) -> PedagogicalDecisionResult:
        session = self._get_owned_session(user_id=user_id, session_id=session_id)
        evaluation_artifact = self.artifacts.get_by_session_and_type(
            session_id=session.id,
            artifact_type=EVALUATION_ARTIFACT_TYPE,
        )
        if evaluation_artifact is None:
            result = self.pedagogical_decision.build_failure_result(
                session_id=session.id,
                sport_id=session.drill.sport_id,
                drill_id=session.drill_id,
                skill_level=session.skill_level,
                diagnostic_flags=["MISSING_EVALUATION_RESULT"],
            )
            self._persist_pedagogical_decision_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        try:
            evaluation_result = DeterministicEvaluationResult(
                **evaluation_artifact.payload_json
            )
        except Exception:
            result = self.pedagogical_decision.build_failure_result(
                session_id=session.id,
                sport_id=session.drill.sport_id,
                drill_id=session.drill_id,
                skill_level=session.skill_level,
                diagnostic_flags=["MALFORMED_EVALUATION_RESULT"],
            )
            self._persist_pedagogical_decision_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        feedback_artifact = self.artifacts.get_by_session_and_type(
            session_id=session.id,
            artifact_type=FEEDBACK_ARTIFACT_TYPE,
        )
        if feedback_artifact is None:
            result = self.pedagogical_decision.build_failure_result(
                session_id=session.id,
                sport_id=session.drill.sport_id,
                drill_id=session.drill_id,
                skill_level=session.skill_level,
                diagnostic_flags=["MISSING_FEEDBACK_RESULT"],
            )
            self._persist_pedagogical_decision_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        try:
            feedback_result = DeterministicFeedbackResult(
                **feedback_artifact.payload_json
            )
        except Exception:
            result = self.pedagogical_decision.build_failure_result(
                session_id=session.id,
                sport_id=session.drill.sport_id,
                drill_id=session.drill_id,
                skill_level=session.skill_level,
                diagnostic_flags=["MALFORMED_FEEDBACK_RESULT"],
            )
            self._persist_pedagogical_decision_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        fuzzy_result = None
        fuzzy_diagnostic_flags: list[str] = []
        fuzzy_artifact = self.artifacts.get_by_session_and_type(
            session_id=session.id,
            artifact_type=FUZZY_INTERPRETATION_ARTIFACT_TYPE,
        )
        if fuzzy_artifact is None:
            fuzzy_diagnostic_flags.append("MISSING_FUZZY_INTERPRETATION_RESULT")
        else:
            try:
                fuzzy_result = FuzzyInterpretationResult(**fuzzy_artifact.payload_json)
            except Exception:
                fuzzy_diagnostic_flags.append("MALFORMED_FUZZY_INTERPRETATION_RESULT")

        result = self.pedagogical_decision.decide(
            evaluation_result=evaluation_result,
            feedback_result=feedback_result,
            fuzzy_result=fuzzy_result,
            diagnostic_flags=fuzzy_diagnostic_flags,
        )
        self._persist_pedagogical_decision_result(session_id=session.id, result=result)
        self.db.commit()
        return result

    def generate_ontology_reasoning(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
    ) -> OntologyReasoningResult:
        session = self._get_owned_session(user_id=user_id, session_id=session_id)
        evaluation_artifact = self.artifacts.get_by_session_and_type(
            session_id=session.id,
            artifact_type=EVALUATION_ARTIFACT_TYPE,
        )
        if evaluation_artifact is None:
            result = self.ontology_reasoning.build_failure_result(
                session_id=session.id,
                sport_id=session.drill.sport_id,
                drill_id=session.drill_id,
                skill_level=session.skill_level,
                diagnostic_flags=["MISSING_EVALUATION_RESULT"],
            )
            self._persist_ontology_reasoning_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        try:
            evaluation_result = DeterministicEvaluationResult(
                **evaluation_artifact.payload_json
            )
        except Exception:
            result = self.ontology_reasoning.build_failure_result(
                session_id=session.id,
                sport_id=session.drill.sport_id,
                drill_id=session.drill_id,
                skill_level=session.skill_level,
                diagnostic_flags=["MALFORMED_EVALUATION_RESULT"],
            )
            self._persist_ontology_reasoning_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        if evaluation_result.status != "COMPLETED":
            result = self.ontology_reasoning.build_failure_result(
                session_id=session.id,
                sport_id=session.drill.sport_id,
                drill_id=session.drill_id,
                skill_level=session.skill_level,
                diagnostic_flags=[
                    "UNUSABLE_EVALUATION_RESULT",
                    f"EVALUATION_STATUS:{evaluation_result.status}",
                ],
            )
            self._persist_ontology_reasoning_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        fuzzy_result = None
        fuzzy_diagnostic_flags: list[str] = []
        fuzzy_artifact = self.artifacts.get_by_session_and_type(
            session_id=session.id,
            artifact_type=FUZZY_INTERPRETATION_ARTIFACT_TYPE,
        )
        if fuzzy_artifact is None:
            fuzzy_diagnostic_flags.append("MISSING_FUZZY_INTERPRETATION_RESULT")
        else:
            try:
                fuzzy_result = FuzzyInterpretationResult(**fuzzy_artifact.payload_json)
            except Exception:
                fuzzy_diagnostic_flags.append("MALFORMED_FUZZY_INTERPRETATION_RESULT")

        pedagogical_result = None
        pedagogy_diagnostic_flags: list[str] = []
        pedagogical_artifact = self.artifacts.get_by_session_and_type(
            session_id=session.id,
            artifact_type=PEDAGOGICAL_ARTIFACT_TYPE,
        )
        if pedagogical_artifact is not None:
            try:
                pedagogical_result = PedagogicalDecisionResult(
                    **pedagogical_artifact.payload_json
                )
            except Exception:
                pedagogy_diagnostic_flags.append(
                    "MALFORMED_PEDAGOGICAL_DECISION_RESULT"
                )

        result = self.ontology_reasoning.reason(
            evaluation_result=evaluation_result,
            fuzzy_result=fuzzy_result,
            pedagogical_result=pedagogical_result,
        )
        if fuzzy_diagnostic_flags or pedagogy_diagnostic_flags:
            result = result.model_copy(
                update={
                    "diagnostic_flags": self._dedupe_strings(
                        [
                            *result.diagnostic_flags,
                            *fuzzy_diagnostic_flags,
                            *pedagogy_diagnostic_flags,
                        ]
                    )
                }
            )

        self._persist_ontology_reasoning_result(session_id=session.id, result=result)
        self.db.commit()
        return result

    def generate_choquet_aggregation(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
    ) -> ChoquetAggregationResult:
        session = self._get_owned_session(user_id=user_id, session_id=session_id)
        evaluation_artifact = self.artifacts.get_by_session_and_type(
            session_id=session.id,
            artifact_type=EVALUATION_ARTIFACT_TYPE,
        )
        if evaluation_artifact is None:
            result = self.choquet_aggregation.build_failure_result(
                session_id=session.id,
                sport_id=session.drill.sport_id,
                drill_id=session.drill_id,
                skill_level=session.skill_level,
                diagnostic_flags=["MISSING_EVALUATION_RESULT"],
            )
            self._persist_choquet_aggregation_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        try:
            evaluation_result = DeterministicEvaluationResult(
                **evaluation_artifact.payload_json
            )
        except Exception:
            result = self.choquet_aggregation.build_failure_result(
                session_id=session.id,
                sport_id=session.drill.sport_id,
                drill_id=session.drill_id,
                skill_level=session.skill_level,
                diagnostic_flags=["MALFORMED_EVALUATION_RESULT"],
            )
            self._persist_choquet_aggregation_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        if evaluation_result.status != "COMPLETED":
            result = self.choquet_aggregation.build_failure_result(
                session_id=session.id,
                sport_id=session.drill.sport_id,
                drill_id=session.drill_id,
                skill_level=session.skill_level,
                diagnostic_flags=[
                    "UNUSABLE_EVALUATION_RESULT",
                    f"EVALUATION_STATUS:{evaluation_result.status}",
                ],
            )
            self._persist_choquet_aggregation_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        ontology_artifact = self.artifacts.get_by_session_and_type(
            session_id=session.id,
            artifact_type=ONTOLOGY_REASONING_ARTIFACT_TYPE,
        )
        if ontology_artifact is None:
            result = self.choquet_aggregation.build_failure_result(
                session_id=session.id,
                sport_id=session.drill.sport_id,
                drill_id=session.drill_id,
                skill_level=session.skill_level,
                diagnostic_flags=["MISSING_ONTOLOGY_REASONING_RESULT"],
            )
            self._persist_choquet_aggregation_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        try:
            ontology_result = OntologyReasoningResult(**ontology_artifact.payload_json)
        except Exception:
            result = self.choquet_aggregation.build_failure_result(
                session_id=session.id,
                sport_id=session.drill.sport_id,
                drill_id=session.drill_id,
                skill_level=session.skill_level,
                diagnostic_flags=["MALFORMED_ONTOLOGY_REASONING_RESULT"],
            )
            self._persist_choquet_aggregation_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        if ontology_result.status not in {"COMPLETED", "NO_SIGNIFICANT_ISSUES"}:
            result = self.choquet_aggregation.build_failure_result(
                session_id=session.id,
                sport_id=session.drill.sport_id,
                drill_id=session.drill_id,
                skill_level=session.skill_level,
                diagnostic_flags=[
                    "UNUSABLE_ONTOLOGY_REASONING_RESULT",
                    f"ONTOLOGY_STATUS:{ontology_result.status}",
                ],
            )
            self._persist_choquet_aggregation_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        fuzzy_result = None
        fuzzy_artifact = self.artifacts.get_by_session_and_type(
            session_id=session.id,
            artifact_type=FUZZY_INTERPRETATION_ARTIFACT_TYPE,
        )
        fuzzy_diagnostic_flags: list[str] = []
        if fuzzy_artifact is None:
            fuzzy_diagnostic_flags.append("MISSING_FUZZY_INTERPRETATION_RESULT")
        else:
            try:
                fuzzy_result = FuzzyInterpretationResult(**fuzzy_artifact.payload_json)
            except Exception:
                fuzzy_diagnostic_flags.append("MALFORMED_FUZZY_INTERPRETATION_RESULT")

        result = self.choquet_aggregation.aggregate(
            evaluation_result=evaluation_result,
            ontology_result=ontology_result,
            fuzzy_result=fuzzy_result,
        )
        if fuzzy_diagnostic_flags:
            result = result.model_copy(
                update={
                    "diagnostic_flags": self._dedupe_strings(
                        [*result.diagnostic_flags, *fuzzy_diagnostic_flags]
                    )
                }
            )
        self._persist_choquet_aggregation_result(session_id=session.id, result=result)
        self.db.commit()
        return result

    def generate_temporal_modeling(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
    ) -> TemporalModelingResult:
        session = self._get_owned_session(user_id=user_id, session_id=session_id)
        pose_artifact = self.artifacts.get_by_session_and_type(
            session_id=session.id,
            artifact_type=POSE_SEQUENCE_ARTIFACT_TYPE,
        )
        if pose_artifact is None:
            result = self.temporal_modeling.build_failure_result(
                session_id=session.id,
                sport_id=session.drill.sport_id,
                drill_id=session.drill_id,
                skill_level=session.skill_level,
                diagnostic_flags=["MISSING_POSE_SEQUENCE"],
            )
            self._persist_temporal_modeling_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        try:
            pose_sequence = PoseSequenceResponse(**pose_artifact.payload_json)
        except Exception:
            result = self.temporal_modeling.build_failure_result(
                session_id=session.id,
                sport_id=session.drill.sport_id,
                drill_id=session.drill_id,
                skill_level=session.skill_level,
                diagnostic_flags=["MALFORMED_POSE_SEQUENCE"],
            )
            self._persist_temporal_modeling_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        if pose_sequence.frame_count <= 0:
            result = self.temporal_modeling.build_failure_result(
                session_id=session.id,
                sport_id=session.drill.sport_id,
                drill_id=session.drill_id,
                skill_level=session.skill_level,
                diagnostic_flags=["UNUSABLE_POSE_SEQUENCE", "POSE_SEQUENCE_EMPTY"],
                status="INSUFFICIENT_DATA",
            )
            self._persist_temporal_modeling_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        evaluation_artifact = self.artifacts.get_by_session_and_type(
            session_id=session.id,
            artifact_type=EVALUATION_ARTIFACT_TYPE,
        )
        if evaluation_artifact is None:
            result = self.temporal_modeling.build_failure_result(
                session_id=session.id,
                sport_id=session.drill.sport_id,
                drill_id=session.drill_id,
                skill_level=session.skill_level,
                diagnostic_flags=["MISSING_EVALUATION_RESULT"],
            )
            self._persist_temporal_modeling_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        try:
            evaluation_result = DeterministicEvaluationResult(
                **evaluation_artifact.payload_json
            )
        except Exception:
            result = self.temporal_modeling.build_failure_result(
                session_id=session.id,
                sport_id=session.drill.sport_id,
                drill_id=session.drill_id,
                skill_level=session.skill_level,
                diagnostic_flags=["MALFORMED_EVALUATION_RESULT"],
            )
            self._persist_temporal_modeling_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        if evaluation_result.status != "COMPLETED":
            result = self.temporal_modeling.build_failure_result(
                session_id=session.id,
                sport_id=session.drill.sport_id,
                drill_id=session.drill_id,
                skill_level=session.skill_level,
                diagnostic_flags=[
                    "UNUSABLE_EVALUATION_RESULT",
                    f"EVALUATION_STATUS:{evaluation_result.status}",
                ],
                status="INSUFFICIENT_DATA",
            )
            self._persist_temporal_modeling_result(session_id=session.id, result=result)
            self.db.commit()
            return result

        fuzzy_result = None
        fuzzy_diagnostic_flags: list[str] = []
        fuzzy_artifact = self.artifacts.get_by_session_and_type(
            session_id=session.id,
            artifact_type=FUZZY_INTERPRETATION_ARTIFACT_TYPE,
        )
        if fuzzy_artifact is None:
            fuzzy_diagnostic_flags.append("MISSING_FUZZY_INTERPRETATION_RESULT")
        else:
            try:
                fuzzy_result = FuzzyInterpretationResult(**fuzzy_artifact.payload_json)
            except Exception:
                fuzzy_diagnostic_flags.append("MALFORMED_FUZZY_INTERPRETATION_RESULT")

        result = self.temporal_modeling.model(
            pose_sequence=pose_sequence,
            evaluation_result=evaluation_result,
            fuzzy_result=fuzzy_result,
        )
        if fuzzy_diagnostic_flags:
            result = result.model_copy(
                update={
                    "diagnostic_flags": self._dedupe_strings(
                        [*result.diagnostic_flags, *fuzzy_diagnostic_flags]
                    )
                }
            )
        self._persist_temporal_modeling_result(session_id=session.id, result=result)
        self.db.commit()
        return result

    def generate_llm_feedback(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
    ) -> LLMFeedbackResult:
        session = self._get_owned_session(user_id=user_id, session_id=session_id)
        evaluation_result = self._load_evaluation_result_for_feedback(session=session)
        feedback_result = self._load_or_generate_feedback_result(
            session=session,
            evaluation_result=evaluation_result,
        )
        result = self.llm_feedback.enhance(
            session=session,
            evaluation_result=evaluation_result,
            feedback_result=feedback_result,
        )
        self._persist_llm_feedback_result(session_id=session.id, result=result)
        self.db.commit()
        return result

    def start_live_session(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        payload: LiveReadinessRequest,
    ) -> LiveStartResponse:
        session = self._get_owned_session(user_id=user_id, session_id=session_id)
        self._ensure_input_type(session, InputType.LIVE)
        self._ensure_session_open(session)

        readiness = self.perception.validate_live_readiness(payload)
        started = (
            readiness.camera_ready
            and readiness.lighting_ready
            and readiness.framing_ready
            and readiness.space_ready
            and payload.client_ready
        )

        message = (
            "Live session started."
            if started
            else "Finish the checks before starting."
        )

        return LiveStartResponse(
            session_id=session.id,
            status=session.status,
            started=started,
            message=message,
            readiness=readiness,
        )

    def accept_live_frame_batch(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        payload: FrameBatchRequest,
    ) -> FrameBatchResponse:
        session = self._get_owned_session(user_id=user_id, session_id=session_id)
        self._ensure_input_type(session, InputType.LIVE)
        self._ensure_session_open(session)

        acceptance = self.perception.accept_frame_batch(payload)
        return FrameBatchResponse(
            session_id=session.id,
            accepted=acceptance.accepted,
            frame_count=acceptance.frame_count,
            message=acceptance.message,
        )

    def end_live_session(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        payload: LiveEndRequest,
    ) -> SessionResponse:
        session = self._get_owned_session(user_id=user_id, session_id=session_id)
        self._ensure_input_type(session, InputType.LIVE)
        self._ensure_session_open(session)

        session.status = payload.final_status
        session.end_time = datetime.now(UTC)

        updated_session = self.sessions.save(session)
        self.db.commit()
        return self._build_session_response(updated_session)

    def _get_owned_session(self, *, user_id: UUID, session_id: UUID) -> TrainingSession:
        session = self.sessions.get_by_id_for_user(user_id=user_id, session_id=session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requested session was not found.",
            )
        return session

    @staticmethod
    def _ensure_input_type(session: TrainingSession, expected: InputType) -> None:
        if session.input_type != expected:
            if expected is InputType.UPLOAD:
                detail = "This session does not accept uploaded media."
            else:
                detail = "This session is not configured for live mode."
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    @staticmethod
    def _ensure_session_open(session: TrainingSession) -> None:
        if session.status is not SessionStatus.ACTIVE or session.end_time is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This session has already ended.",
            )

    @staticmethod
    def _resolve_tracked_joints(session: TrainingSession) -> list[str]:
        reference_payload = session.drill.reference_payload or {}
        tracked_joints = reference_payload.get("tracked_joints")
        if isinstance(tracked_joints, list) and tracked_joints:
            return [str(joint) for joint in tracked_joints]
        return ["shoulders", "hips", "knees", "ankles"]

    @staticmethod
    def _ensure_sport_matches_drill(*, drill: Drill, sport_id: UUID) -> None:
        if drill.sport_id != sport_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Requested sport does not match the requested drill.",
            )

    @staticmethod
    def _ensure_dominant_side_requirement(
        *,
        drill: Drill,
        payload: SessionCreateRequest,
    ) -> None:
        contract = get_phase2a_contract(drill.drill_name)
        reference_payload = drill.reference_payload or {}
        requires_dominant_side = (
            contract.requires_dominant_side
            if contract is not None
            else bool(reference_payload.get("requires_dominant_side"))
        )
        if requires_dominant_side and payload.dominant_side is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"dominant_side is required for {drill.drill_name} sessions.",
            )

    @staticmethod
    def _build_session_response(session: TrainingSession) -> SessionResponse:
        sport = session.drill.sport if session.drill is not None else None
        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            drill_id=session.drill_id,
            sport_id=session.drill.sport_id,
            skill_level=session.skill_level,
            input_type=session.input_type,
            camera_view=session.camera_view,
            dominant_side=session.dominant_side,
            status=session.status,
            start_time=session.start_time,
            end_time=session.end_time,
            drill_name=session.drill.drill_name,
            sport_name=sport.sport_name if sport is not None else "",
        )

    @staticmethod
    def _build_feedback_response(feedback_row) -> FeedbackResponse:
        return FeedbackResponse(
            id=feedback_row.id,
            session_id=feedback_row.session_id,
            severity_level=feedback_row.severity_level,
            technique_issue=feedback_row.technique_issue,
            coaching_cue=feedback_row.coaching_cue,
            metric_snapshot=feedback_row.metric_snapshot,
            created_at=feedback_row.created_at,
        )

    @staticmethod
    def _build_pose_sequence_summary_response(
        *,
        pose_sequence: PoseSequenceResponse,
    ) -> PoseSequenceSummaryResponse:
        return PoseSequenceSummaryResponse(
            session_id=pose_sequence.session_id,
            pose_model=pose_sequence.pose_model,
            preprocessing_version=pose_sequence.preprocessing_version,
            frame_count=pose_sequence.frame_count,
            valid_frame_count=pose_sequence.valid_frame_count,
            status=pose_sequence.status,
            diagnostic_flags=pose_sequence.diagnostic_flags,
        )

    def _clear_phase0_outputs(self, *, session_id: UUID) -> None:
        self.artifacts.delete_by_session_and_types(
            session_id=session_id,
            artifact_types=[
                PERCEPTION_ARTIFACT_TYPE,
                COGNITION_ARTIFACT_TYPE,
                EVALUATION_ARTIFACT_TYPE,
                FEEDBACK_ARTIFACT_TYPE,
                LLM_FEEDBACK_ARTIFACT_TYPE,
                FUZZY_INTERPRETATION_ARTIFACT_TYPE,
                IT2_FUZZY_INTERPRETATION_ARTIFACT_TYPE,
                PEDAGOGICAL_ARTIFACT_TYPE,
                ONTOLOGY_REASONING_ARTIFACT_TYPE,
                CHOQUET_AGGREGATION_ARTIFACT_TYPE,
                TEMPORAL_MODELING_ARTIFACT_TYPE,
            ],
        )
        self.feedback.delete_by_session_id(session_id=session_id)
        self.metric_results.delete_by_session_id(session_id=session_id)

        existing_summary = self.summaries.get_by_session_id(session_id=session_id)
        if existing_summary is not None:
            self.progress_records.delete_by_summary_id(summary_id=existing_summary.id)
            self.summaries.delete_by_session_id(session_id=session_id)

    def _replace_metric_results(
        self,
        *,
        session_id: UUID,
        metric_results: list[MetricEvaluationResultResponse],
        metric_types_by_name: dict[str, MetricType] | None = None,
    ) -> None:
        self.metric_results.delete_by_session_id(session_id=session_id)
        if not metric_results:
            return

        if metric_types_by_name is None:
            raise ValueError("metric_types_by_name is required when metric_results are provided.")

        for metric_result in metric_results:
            metric_type = metric_types_by_name[metric_result.metric_name]
            self.metric_results.create(
                session_id=session_id,
                metric_id=metric_type.id,
                phase_id=metric_result.phase_id,
                raw_value=self._decimal_or_none(metric_result.raw_value),
                unit=metric_result.unit,
                ideal_min=self._decimal_or_none(metric_result.ideal_min),
                ideal_max=self._decimal_or_none(metric_result.ideal_max),
                deviation=self._decimal_or_none(metric_result.deviation),
                severity_level=metric_result.severity_level,
                normalized_score=self._decimal_or_none(metric_result.normalized_score),
                affected_body_part=metric_result.affected_body_part,
                computation_status=metric_result.computation_status,
                valid_frame_count=metric_result.valid_frame_count,
                formula_version=metric_result.formula_version,
            )

    def _persist_evaluation_result(
        self,
        *,
        session_id: UUID,
        result: DeterministicEvaluationResult,
    ) -> None:
        self._clear_feedback_outputs(session_id=session_id)
        self.artifacts.delete_by_session_and_types(
            session_id=session_id,
            artifact_types=[
                FUZZY_INTERPRETATION_ARTIFACT_TYPE,
                IT2_FUZZY_INTERPRETATION_ARTIFACT_TYPE,
                ONTOLOGY_REASONING_ARTIFACT_TYPE,
                CHOQUET_AGGREGATION_ARTIFACT_TYPE,
                TEMPORAL_MODELING_ARTIFACT_TYPE,
            ],
        )
        self.artifacts.upsert(
            session_id=session_id,
            artifact_type=EVALUATION_ARTIFACT_TYPE,
            payload_json=result.model_dump(mode="json"),
        )

    def _clear_feedback_outputs(self, *, session_id: UUID) -> None:
        self.feedback.delete_by_session_id(session_id=session_id)
        self.artifacts.delete_by_session_and_types(
            session_id=session_id,
            artifact_types=[
                FEEDBACK_ARTIFACT_TYPE,
                LLM_FEEDBACK_ARTIFACT_TYPE,
                PEDAGOGICAL_ARTIFACT_TYPE,
                ONTOLOGY_REASONING_ARTIFACT_TYPE,
            ],
        )

    def _replace_feedback_outputs(
        self,
        *,
        session_id: UUID,
        result: DeterministicFeedbackResult,
    ) -> None:
        self._clear_feedback_outputs(session_id=session_id)
        for item in result.prioritized_feedback_items:
            self._create_feedback_row(
                session_id=session_id,
                item=item,
                feedback_version=result.feedback_version,
            )
        self._persist_feedback_result(session_id=session_id, result=result)

    def _create_feedback_row(
        self,
        *,
        session_id: UUID,
        item: DeterministicFeedbackItemResponse,
        feedback_version: str,
    ) -> None:
        self.feedback.create(
            session_id=session_id,
            severity_level=item.severity_level,
            technique_issue=item.issue_title,
            coaching_cue=item.coaching_cue,
            metric_snapshot={
                "feedback_version": feedback_version,
                "phase_id": item.phase_id,
                "metric_id": item.metric_id,
                "metric_name": item.metric_name,
                "affected_body_part": item.affected_body_part,
                "issue_direction": item.issue_direction,
                "priority_rank": item.priority_rank,
                "deviation": item.deviation,
                "improvement_suggestion": item.improvement_suggestion,
            },
        )

    def _persist_feedback_result(
        self,
        *,
        session_id: UUID,
        result: DeterministicFeedbackResult,
    ) -> None:
        self.artifacts.upsert(
            session_id=session_id,
            artifact_type=FEEDBACK_ARTIFACT_TYPE,
            payload_json=result.model_dump(mode="json"),
        )

    def _persist_fuzzy_interpretation_result(
        self,
        *,
        session_id: UUID,
        result: FuzzyInterpretationResult,
    ) -> None:
        self.artifacts.delete_by_session_and_types(
            session_id=session_id,
            artifact_types=[
                IT2_FUZZY_INTERPRETATION_ARTIFACT_TYPE,
                PEDAGOGICAL_ARTIFACT_TYPE,
                ONTOLOGY_REASONING_ARTIFACT_TYPE,
                CHOQUET_AGGREGATION_ARTIFACT_TYPE,
                TEMPORAL_MODELING_ARTIFACT_TYPE,
            ],
        )
        self.artifacts.upsert(
            session_id=session_id,
            artifact_type=FUZZY_INTERPRETATION_ARTIFACT_TYPE,
            payload_json=result.model_dump(mode="json"),
        )

    def _persist_it2_fuzzy_interpretation_result(
        self,
        *,
        session_id: UUID,
        result: IT2FuzzyInterpretationResult,
    ) -> None:
        self.artifacts.upsert(
            session_id=session_id,
            artifact_type=IT2_FUZZY_INTERPRETATION_ARTIFACT_TYPE,
            payload_json=result.model_dump(mode="json"),
        )

    def _persist_pedagogical_decision_result(
        self,
        *,
        session_id: UUID,
        result: PedagogicalDecisionResult,
    ) -> None:
        self.artifacts.delete_by_session_and_types(
            session_id=session_id,
            artifact_types=[ONTOLOGY_REASONING_ARTIFACT_TYPE],
        )
        self.artifacts.upsert(
            session_id=session_id,
            artifact_type=PEDAGOGICAL_ARTIFACT_TYPE,
            payload_json=result.model_dump(mode="json"),
        )

    def _persist_ontology_reasoning_result(
        self,
        *,
        session_id: UUID,
        result: OntologyReasoningResult,
    ) -> None:
        self.artifacts.delete_by_session_and_types(
            session_id=session_id,
            artifact_types=[CHOQUET_AGGREGATION_ARTIFACT_TYPE],
        )
        self.artifacts.upsert(
            session_id=session_id,
            artifact_type=ONTOLOGY_REASONING_ARTIFACT_TYPE,
            payload_json=result.model_dump(mode="json"),
        )

    def _persist_choquet_aggregation_result(
        self,
        *,
        session_id: UUID,
        result: ChoquetAggregationResult,
    ) -> None:
        self.artifacts.upsert(
            session_id=session_id,
            artifact_type=CHOQUET_AGGREGATION_ARTIFACT_TYPE,
            payload_json=result.model_dump(mode="json"),
        )

    def _persist_temporal_modeling_result(
        self,
        *,
        session_id: UUID,
        result: TemporalModelingResult,
    ) -> None:
        self.artifacts.upsert(
            session_id=session_id,
            artifact_type=TEMPORAL_MODELING_ARTIFACT_TYPE,
            payload_json=result.model_dump(mode="json"),
        )

    def _persist_llm_feedback_result(
        self,
        *,
        session_id: UUID,
        result: LLMFeedbackResult,
    ) -> None:
        self.artifacts.upsert(
            session_id=session_id,
            artifact_type=LLM_FEEDBACK_ARTIFACT_TYPE,
            payload_json=result.model_dump(mode="json"),
        )

    def _load_evaluation_result_for_feedback(
        self,
        *,
        session: TrainingSession,
    ) -> DeterministicEvaluationResult:
        evaluation_artifact = self.artifacts.get_by_session_and_type(
            session_id=session.id,
            artifact_type=EVALUATION_ARTIFACT_TYPE,
        )
        if evaluation_artifact is None:
            return self._build_evaluation_failure(
                session=session,
                diagnostic_flags=["MISSING_EVALUATION_RESULT"],
            )

        try:
            return DeterministicEvaluationResult(**evaluation_artifact.payload_json)
        except Exception:
            return self._build_evaluation_failure(
                session=session,
                diagnostic_flags=["MALFORMED_EVALUATION_RESULT"],
            )

    def _load_or_generate_feedback_result(
        self,
        *,
        session: TrainingSession,
        evaluation_result: DeterministicEvaluationResult,
    ) -> DeterministicFeedbackResult:
        feedback_artifact = self.artifacts.get_by_session_and_type(
            session_id=session.id,
            artifact_type=FEEDBACK_ARTIFACT_TYPE,
        )
        if feedback_artifact is not None:
            try:
                return DeterministicFeedbackResult(**feedback_artifact.payload_json)
            except Exception:
                pass

        feedback_result = self.deterministic_feedback.generate(
            evaluation_result=evaluation_result,
        )
        self._replace_feedback_outputs(session_id=session.id, result=feedback_result)
        return feedback_result

    @staticmethod
    def _build_evaluation_failure(
        *,
        session: TrainingSession,
        diagnostic_flags: list[str],
        result_status: str = "FAILED",
    ) -> DeterministicEvaluationResult:
        return DeterministicEvaluationResult(
            evaluation_version=PHASE2A_EVALUATION_VERSION,
            status=result_status,
            session_id=session.id,
            sport_id=session.drill.sport_id,
            skill_level=session.skill_level,
            drill_id=session.drill_id,
            phase_results=[],
            overall_score=0.0,
            overall_severity=SeverityLevel.SEVERE,
            detected_issues=[],
            strongest_metrics=[],
            weakest_metrics=[],
            diagnostic_flags=diagnostic_flags,
        )

    @staticmethod
    def _build_feedback_failure(
        *,
        session: TrainingSession,
        diagnostic_flags: list[str],
        summary: str,
    ) -> DeterministicFeedbackResult:
        return DeterministicFeedbackResult(
            status="FAILED",
            session_id=session.id,
            overall_feedback_summary=summary,
            prioritized_feedback_items=[],
            improvement_suggestions=[],
            diagnostic_flags=diagnostic_flags,
            created_at=datetime.now(UTC),
        )

    @staticmethod
    def _decimal_or_none(value: float | None) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))

    @staticmethod
    def _dedupe_strings(values: list[str]) -> list[str]:
        deduped: list[str] = []
        for value in values:
            if value not in deduped:
                deduped.append(value)
        return deduped

    @staticmethod
    def _build_next_step(*, pose_sequence: PoseSequenceResponse) -> str:
        if pose_sequence.status == "COMPLETED":
            return "Pose sequence saved. Ready for deterministic evaluation."
        if pose_sequence.status == "INSUFFICIENT_DATA":
            return "Pose sequence saved, but the clip needs more usable pose data."
        return "Pose extraction failed. Upload a different clip and try again."

    @staticmethod
    def _build_session_summary_response(summary: SessionSummary) -> SessionSummaryResponse:
        return SessionSummaryResponse(
            id=summary.id,
            session_id=summary.session_id,
            summary_text=summary.summary_text,
            overall_accuracy=float(summary.overall_accuracy),
            strengths=summary.strengths,
            weaknesses=summary.weaknesses,
            recommendations=summary.recommendations,
            created_at=summary.created_at,
        )
