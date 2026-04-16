from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.engines.cognition_engine.cognition_service import CognitionService
from app.engines.perception_interface.perception_service import PerceptionService
from app.models.enums import InputType, SessionStatus
from app.models.training_session import TrainingSession
from app.repositories.drill_repository import DrillRepository
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.session_artifact_repository import SessionArtifactRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.session import (
    CognitionResult,
    DrillEvaluationResult,
    FeedbackResponse,
    FrameBatchRequest,
    FrameBatchResponse,
    LiveEndRequest,
    LiveReadinessRequest,
    LiveStartResponse,
    PerceptionResult,
    SessionCreateRequest,
    SessionArtifactsResponse,
    SessionArtifactResponse,
    SessionResponse,
    UploadProcessingResponse,
)

PERCEPTION_ARTIFACT_TYPE = "perception_payload"
COGNITION_ARTIFACT_TYPE = "cognition_result"
EVALUATION_ARTIFACT_TYPE = "evaluation_result"


@dataclass
class SessionService:
    db: Session
    sessions: SessionRepository
    artifacts: SessionArtifactRepository
    feedback: FeedbackRepository
    drills: DrillRepository
    perception: PerceptionService
    cognition: CognitionService

    def create_session(self, *, user_id: UUID, payload: SessionCreateRequest) -> SessionResponse:
        drill = self.drills.get_by_id(payload.drill_id)
        if drill is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requested drill was not found.",
            )

        session = self.sessions.create(
            user_id=user_id,
            drill_id=payload.drill_id,
            input_type=payload.input_type,
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

        validation = self.perception.validate_upload(
            file_name=file_name,
            content_type=content_type,
            file_size_bytes=file_size_bytes,
        )

        next_step = (
            "Drill-specific analysis and coaching feedback will be connected next."
            if validation.is_valid
            else "Upload validation failed. Resolve the file issues and retry."
        )

        if not validation.is_valid:
            return UploadProcessingResponse(
                session_id=session.id,
                status=session.status,
                upload_received=False,
                validation=validation,
                next_step=next_step,
            )

        tracked_joints = self._resolve_tracked_joints(session)
        perception_result = self.perception.process_uploaded_file(
            session_id=session.id,
            drill_id=session.drill_id,
            file_name=file_name or "uploaded-video",
            content_type=validation.content_type or "application/octet-stream",
            file_size_bytes=file_size_bytes,
            tracked_joints=tracked_joints,
            file_bytes=file_bytes,
        )
        cognition_result = self.cognition.analyze_perception_payload(
            session_id=session.id,
            drill_id=session.drill_id,
            perception_result=perception_result,
        )
        evaluation_result = self.cognition.evaluate_drill_payload(
            perception_result=perception_result,
            drill=session.drill,
            session=session,
        )

        self.artifacts.upsert(
            session_id=session.id,
            artifact_type=PERCEPTION_ARTIFACT_TYPE,
            payload_json=perception_result.model_dump(mode="json"),
        )
        self.artifacts.upsert(
            session_id=session.id,
            artifact_type=COGNITION_ARTIFACT_TYPE,
            payload_json=cognition_result.model_dump(mode="json"),
        )
        self.artifacts.upsert(
            session_id=session.id,
            artifact_type=EVALUATION_ARTIFACT_TYPE,
            payload_json=evaluation_result.model_dump(mode="json"),
        )
        self.feedback.delete_by_session_id(session_id=session.id)
        feedback_rows = [
            self.feedback.create(
                session_id=session.id,
                severity_level=issue.severity_level,
                technique_issue=issue.issue_label,
                coaching_cue=issue.coaching_cue,
                metric_snapshot={
                    "metric": issue.metric,
                    "actual_score": issue.actual_score,
                    "expected_min": issue.expected_min,
                    "expected_max": issue.expected_max,
                    "deviation": issue.deviation,
                    "evaluator_name": evaluation_result.evaluator_name,
                    "drill_name": evaluation_result.drill_name,
                },
            )
            for issue in evaluation_result.issues
        ]
        self.db.commit()

        return UploadProcessingResponse(
            session_id=session.id,
            status=session.status,
            upload_received=True,
            validation=validation,
            perception_result=perception_result,
            cognition_result=cognition_result,
            evaluation_result=evaluation_result,
            feedback=[self._build_feedback_response(row) for row in feedback_rows],
            artifacts_persisted=[
                PERCEPTION_ARTIFACT_TYPE,
                COGNITION_ARTIFACT_TYPE,
                EVALUATION_ARTIFACT_TYPE,
            ],
            next_step="Session summary and progress tracking will be connected next.",
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

        perception_result: PerceptionResult | None = None
        cognition_result: CognitionResult | None = None
        evaluation_result: DrillEvaluationResult | None = None

        for artifact in artifacts:
            if artifact.artifact_type == PERCEPTION_ARTIFACT_TYPE:
                perception_result = PerceptionResult(**artifact.payload_json)
            elif artifact.artifact_type == COGNITION_ARTIFACT_TYPE:
                cognition_result = CognitionResult(**artifact.payload_json)
            elif artifact.artifact_type == EVALUATION_ARTIFACT_TYPE:
                evaluation_result = DrillEvaluationResult(**artifact.payload_json)

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
            perception_result=perception_result,
            cognition_result=cognition_result,
            evaluation_result=evaluation_result,
            feedback=[self._build_feedback_response(row) for row in feedback_rows],
        )

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
            "Live session scaffold started. Real-time perception hooks will connect next."
            if started
            else "Live readiness checks are incomplete. Resolve the warnings before starting."
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
    def _build_session_response(session: TrainingSession) -> SessionResponse:
        sport = session.drill.sport if session.drill is not None else None
        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            drill_id=session.drill_id,
            sport_id=session.drill.sport_id,
            input_type=session.input_type,
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
