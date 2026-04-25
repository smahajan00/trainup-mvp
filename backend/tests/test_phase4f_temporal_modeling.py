from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import select

from app.engines.temporal_engine.temporal_contract import TEMPORAL_MODEL_VERSION
from app.models.drill import Drill
from app.models.enums import ComputationStatus, SeverityLevel
from app.models.session_artifact import SessionArtifact
from app.schemas.session import (
    DeterministicEvaluationIssueResponse,
    DeterministicEvaluationResult,
    EvaluationFrameRangeResponse,
    FuzzyInterpretationResult,
    FuzzyMetricInterpretationResponse,
    FuzzySummaryResponse,
    MetricEvaluationResultResponse,
    PhaseEvaluationResultResponse,
    PoseFrameResponse,
    PoseLandmarkCoordinate,
    PoseSequenceResponse,
    RankedMetricResponse,
)
from app.services.temporal_modeling_service import (
    TemporalModelingService,
    assign_temporal_state,
    compute_acceleration_change_proxy,
    compute_average_velocity_proxy,
    compute_smoothness_proxy,
    compute_valid_frame_ratio,
    compute_velocity_sequence,
)


def _register_user(client, *, email: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Phase 4F Temporal",
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


def _landmark(x: float, y: float, visibility: float = 0.96) -> PoseLandmarkCoordinate:
    return PoseLandmarkCoordinate(x=round(x, 6), y=round(y, 6), visibility=visibility)


def _frame(
    *,
    session_id: str,
    frame_index: int,
    center_x: float,
    center_y: float,
    valid: bool = True,
    include_keypoints: bool = True,
) -> PoseFrameResponse:
    landmarks = (
        {
            "nose": _landmark(center_x, center_y - 0.18),
            "left_shoulder": _landmark(center_x - 0.08, center_y - 0.08),
            "right_shoulder": _landmark(center_x + 0.08, center_y - 0.08),
            "left_elbow": _landmark(center_x - 0.10, center_y + 0.02),
            "right_elbow": _landmark(center_x + 0.10, center_y + 0.02),
            "left_wrist": _landmark(center_x - 0.11, center_y + 0.12),
            "right_wrist": _landmark(center_x + 0.11, center_y + 0.12),
            "left_hip": _landmark(center_x - 0.06, center_y + 0.16),
            "right_hip": _landmark(center_x + 0.06, center_y + 0.16),
            "left_knee": _landmark(center_x - 0.06, center_y + 0.33),
            "right_knee": _landmark(center_x + 0.06, center_y + 0.33),
            "left_ankle": _landmark(center_x - 0.06, center_y + 0.50),
            "right_ankle": _landmark(center_x + 0.06, center_y + 0.50),
            "left_heel": _landmark(center_x - 0.08, center_y + 0.52),
            "right_heel": _landmark(center_x + 0.08, center_y + 0.52),
            "left_foot_index": _landmark(center_x - 0.04, center_y + 0.55),
            "right_foot_index": _landmark(center_x + 0.04, center_y + 0.55),
        }
        if include_keypoints
        else {}
    )
    return PoseFrameResponse(
        session_id=UUID(session_id),
        frame_index=frame_index,
        timestamp_ms=frame_index * 40.0,
        landmarks=landmarks,
        frame_valid=valid,
        diagnostic_flags=[],
    )


def _pose_sequence(session_id: str, frames: list[PoseFrameResponse]) -> PoseSequenceResponse:
    return PoseSequenceResponse(
        session_id=UUID(session_id),
        pose_model="mediapipe_pose",
        preprocessing_version="phase1_v0_1_0",
        frame_count=len(frames),
        valid_frame_count=sum(frame.frame_valid for frame in frames),
        status="COMPLETED",
        diagnostic_flags=[],
        sequence_data=frames,
        created_at=None,
    )


def _store_pose_sequence(db_session, *, session_id: str, frames: list[PoseFrameResponse]) -> None:
    pose_sequence = _pose_sequence(session_id, frames)
    db_session.add(
        SessionArtifact(
            session_id=UUID(session_id),
            artifact_type="pose_sequence",
            payload_json=pose_sequence.model_dump(mode="json", exclude={"created_at"}),
        )
    )
    db_session.commit()


def _metric_result(
    *,
    metric_id: str,
    phase_id: str,
    affected_body_part: str,
    severity_level: SeverityLevel = SeverityLevel.MODERATE,
) -> MetricEvaluationResultResponse:
    return MetricEvaluationResultResponse(
        metric_id=metric_id,
        metric_name=metric_id,
        phase_id=phase_id,
        raw_value=0.7,
        unit="score",
        ideal_min=0.8,
        ideal_max=1.0,
        deviation=0.18,
        issue_direction="UNDER_RANGE",
        severity_level=severity_level,
        normalized_score=0.7,
        affected_body_part=affected_body_part,
        computation_status=ComputationStatus.COMPUTED,
        valid_frame_count=8,
        formula_version="phase0_v0_1_0",
        diagnostic_flags=[],
    )


def _evaluation_result(
    *,
    session_id: str,
    drill: Drill,
    phase_specs: list[tuple[str, int, int, str]],
) -> DeterministicEvaluationResult:
    phase_results: list[PhaseEvaluationResultResponse] = []
    detected_issues: list[DeterministicEvaluationIssueResponse] = []
    for phase_id, start_frame, end_frame, affected_body_part in phase_specs:
        metric = _metric_result(
            metric_id=f"{phase_id}_timing_metric",
            phase_id=phase_id,
            affected_body_part=affected_body_part,
        )
        issue = DeterministicEvaluationIssueResponse(
            phase_id=phase_id,
            metric_id=metric.metric_id,
            metric_name=metric.metric_name,
            severity_level=metric.severity_level,
            affected_body_part=metric.affected_body_part,
            deviation=metric.deviation or 0.0,
            issue_direction=metric.issue_direction,
            computation_status=metric.computation_status,
            diagnostic_flags=[],
        )
        detected_issues.append(issue)
        phase_results.append(
            PhaseEvaluationResultResponse(
                phase_id=phase_id,
                frame_range=EvaluationFrameRangeResponse(
                    phase_id=phase_id,
                    start_frame_index=start_frame,
                    end_frame_index=end_frame,
                    start_timestamp_ms=start_frame * 40.0,
                    end_timestamp_ms=end_frame * 40.0,
                ),
                metric_results=[metric],
                phase_score=0.7,
                phase_severity=metric.severity_level,
                detected_issues=[issue],
            )
        )

    return DeterministicEvaluationResult(
        status="COMPLETED",
        session_id=UUID(session_id),
        sport_id=drill.sport_id,
        skill_level="BEGINNER",
        drill_id=drill.id,
        phase_results=phase_results,
        overall_score=0.7,
        overall_severity=SeverityLevel.MODERATE,
        detected_issues=detected_issues,
        strongest_metrics=[
            RankedMetricResponse(
                phase_id=phase_results[0].phase_id,
                metric_id=phase_results[0].metric_results[0].metric_id or "metric",
                metric_name=phase_results[0].metric_results[0].metric_name,
                score=0.85,
            )
        ],
        weakest_metrics=[
            RankedMetricResponse(
                phase_id=phase_results[-1].phase_id,
                metric_id=phase_results[-1].metric_results[0].metric_id or "metric",
                metric_name=phase_results[-1].metric_results[0].metric_name,
                score=0.55,
            )
        ],
        diagnostic_flags=[],
    )


def _store_evaluation_artifact(
    db_session,
    *,
    session_id: str,
    evaluation_result: DeterministicEvaluationResult,
) -> None:
    db_session.add(
        SessionArtifact(
            session_id=UUID(session_id),
            artifact_type="evaluation_result",
            payload_json=evaluation_result.model_dump(mode="json"),
        )
    )
    db_session.commit()


def _fuzzy_result(
    *,
    session_id: str,
    drill: Drill,
    phase_id: str,
    metric_id: str,
    confidence: float,
) -> FuzzyInterpretationResult:
    return FuzzyInterpretationResult(
        status="COMPLETED",
        session_id=UUID(session_id),
        drill_id=drill.id,
        sport_id=drill.sport_id,
        skill_level="BEGINNER",
        fuzzy_metric_results=[
            FuzzyMetricInterpretationResponse(
                metric_id=metric_id,
                metric_name=metric_id,
                phase_id=phase_id,
                computation_status=ComputationStatus.COMPUTED,
                deviation=0.18,
                issue_direction="UNDER_RANGE",
                severity_level=SeverityLevel.MODERATE,
                affected_body_part="knees",
                primary_fuzzy_label="MODERATELY_OFF",
                membership_scores={
                    "IDEAL": 0.02,
                    "SLIGHTLY_OFF": 0.12,
                    "MODERATELY_OFF": confidence,
                    "STRONGLY_OFF": 0.05,
                },
                dominant_label_confidence=confidence,
                direction_aware_label="MODERATELY_LOW",
                diagnostic_flags=[],
            )
        ],
        fuzzy_summary=FuzzySummaryResponse(
            ideal_count=0,
            slightly_off_count=0,
            moderately_off_count=1,
            strongly_off_count=0,
            not_interpretable_count=0,
            interpretable_metric_count=1,
            dominant_fuzzy_label="MODERATELY_OFF",
            top_concern_areas=["knees"],
        ),
        diagnostic_flags=[],
    )


def test_phase4f_feature_proxies_from_pose_frames() -> None:
    session_id = str(UUID("00000000-0000-0000-0000-000000000001"))
    frames = [
        _frame(session_id=session_id, frame_index=0, center_x=0.50, center_y=0.20),
        _frame(session_id=session_id, frame_index=1, center_x=0.52, center_y=0.21),
        _frame(session_id=session_id, frame_index=2, center_x=0.54, center_y=0.22, valid=False),
        _frame(session_id=session_id, frame_index=3, center_x=0.56, center_y=0.23),
    ]

    ratio = compute_valid_frame_ratio(frames)
    velocities = compute_velocity_sequence(
        frames=frames,
        keypoints=("left_shoulder", "right_shoulder", "left_hip", "right_hip"),
        config=TemporalModelingService().config,
    )
    average_velocity = compute_average_velocity_proxy(velocities)
    acceleration_change = compute_acceleration_change_proxy(velocities)
    smoothness = compute_smoothness_proxy(acceleration_change)

    assert ratio == 0.75
    assert velocities
    assert average_velocity > 0
    assert 0.0 <= acceleration_change <= 1.0
    assert 0.0 <= smoothness <= 1.0


def test_phase4f_state_assignment_supports_stable_rushed_and_incomplete() -> None:
    config = TemporalModelingService().config

    stable_state, stable_confidence = assign_temporal_state(
        frame_count=5,
        phase_duration_ms=240.0,
        valid_frame_ratio=1.0,
        average_velocity_proxy=0.12,
        smoothness_proxy=0.90,
        acceleration_change_proxy=0.05,
        fuzzy_confidence=0.88,
        diagnostic_flags=[],
        config=config,
    )
    rushed_state, rushed_confidence = assign_temporal_state(
        frame_count=4,
        phase_duration_ms=80.0,
        valid_frame_ratio=0.95,
        average_velocity_proxy=0.82,
        smoothness_proxy=0.70,
        acceleration_change_proxy=0.10,
        fuzzy_confidence=0.85,
        diagnostic_flags=[],
        config=config,
    )
    incomplete_state, incomplete_confidence = assign_temporal_state(
        frame_count=1,
        phase_duration_ms=0.0,
        valid_frame_ratio=0.30,
        average_velocity_proxy=0.0,
        smoothness_proxy=0.0,
        acceleration_change_proxy=0.0,
        fuzzy_confidence=None,
        diagnostic_flags=["MISSING_PHASE_FRAMES"],
        config=config,
    )

    assert stable_state == "STABLE"
    assert rushed_state == "RUSHED"
    assert incomplete_state == "INCOMPLETE"
    assert 0.0 <= stable_confidence <= 1.0
    assert 0.0 <= rushed_confidence <= 1.0
    assert 0.0 <= incomplete_confidence <= 1.0


def test_phase4f_low_fuzzy_confidence_can_yield_uncertain_state() -> None:
    state, confidence = assign_temporal_state(
        frame_count=5,
        phase_duration_ms=220.0,
        valid_frame_ratio=0.92,
        average_velocity_proxy=0.18,
        smoothness_proxy=0.74,
        acceleration_change_proxy=0.12,
        fuzzy_confidence=0.30,
        diagnostic_flags=[],
        config=TemporalModelingService().config,
    )

    assert state == "UNCERTAIN"
    assert confidence > 0.0


def test_phase4f_api_persists_temporal_artifact_and_transition_results(client, db_session) -> None:
    token = _register_user(client, email="phase4f-persist@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)
    frames = [
        _frame(session_id=session["id"], frame_index=index, center_x=0.50 + (index * 0.01), center_y=0.20 + (index * 0.015))
        for index in range(6)
    ]
    _store_pose_sequence(db_session, session_id=session["id"], frames=frames)
    _store_evaluation_artifact(
        db_session,
        session_id=session["id"],
        evaluation_result=_evaluation_result(
            session_id=session["id"],
            drill=drill,
            phase_specs=[
                ("setup", 0, 1, "knees"),
                ("descent", 1, 3, "knees"),
                ("ascent", 3, 5, "knees"),
            ],
        ),
    )

    response = client.post(
        f"/api/sessions/{session['id']}/model/temporal",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["temporal_model_version"] == TEMPORAL_MODEL_VERSION
    assert payload["status"] == "COMPLETED"
    assert len(payload["phase_temporal_results"]) == 3
    assert len(payload["transition_results"]) == 2
    assert payload["transition_results"][0]["transition_valid"] is True

    artifacts_response = client.get(
        f"/api/sessions/{session['id']}/artifacts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert artifacts_response.status_code == 200
    assert (
        artifacts_response.json()["temporal_modeling_result"]["temporal_model_version"]
        == TEMPORAL_MODEL_VERSION
    )


def test_phase4f_artifact_upsert_replaces_previous_result(client, db_session) -> None:
    token = _register_user(client, email="phase4f-upsert@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)
    frames = [
        _frame(session_id=session["id"], frame_index=index, center_x=0.50 + (index * 0.005), center_y=0.20 + (index * 0.01))
        for index in range(6)
    ]
    _store_pose_sequence(db_session, session_id=session["id"], frames=frames)
    _store_evaluation_artifact(
        db_session,
        session_id=session["id"],
        evaluation_result=_evaluation_result(
            session_id=session["id"],
            drill=drill,
            phase_specs=[
                ("setup", 0, 1, "knees"),
                ("descent", 1, 3, "knees"),
            ],
        ),
    )

    response = client.post(
        f"/api/sessions/{session['id']}/model/temporal",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    first_phase_count = len(response.json()["phase_temporal_results"])

    artifact = db_session.scalar(
        select(SessionArtifact).where(
            SessionArtifact.session_id == UUID(session["id"]),
            SessionArtifact.artifact_type == "evaluation_result",
        )
    )
    assert artifact is not None
    artifact.payload_json = _evaluation_result(
        session_id=session["id"],
        drill=drill,
        phase_specs=[
            ("setup", 0, 1, "knees"),
            ("descent", 1, 2, "knees"),
            ("ascent", 2, 5, "knees"),
        ],
    ).model_dump(mode="json")
    db_session.add(artifact)
    db_session.commit()

    response = client.post(
        f"/api/sessions/{session['id']}/model/temporal",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert len(response.json()["phase_temporal_results"]) == 3
    assert len(response.json()["phase_temporal_results"]) != first_phase_count

    temporal_artifacts = db_session.scalars(
        select(SessionArtifact).where(
            SessionArtifact.session_id == UUID(session["id"]),
            SessionArtifact.artifact_type == "temporal_modeling_result",
        )
    ).all()
    assert len(temporal_artifacts) == 1


def test_phase4f_missing_pose_sequence_returns_failure(client, db_session) -> None:
    token = _register_user(client, email="phase4f-missing-pose@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)

    response = client.post(
        f"/api/sessions/{session['id']}/model/temporal",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "FAILED"
    assert "MISSING_POSE_SEQUENCE" in payload["diagnostic_flags"]


def test_phase4f_missing_fuzzy_still_completes_safely(client, db_session) -> None:
    token = _register_user(client, email="phase4f-missing-fuzzy@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)
    frames = [
        _frame(session_id=session["id"], frame_index=index, center_x=0.50 + (index * 0.01), center_y=0.20 + (index * 0.01))
        for index in range(5)
    ]
    _store_pose_sequence(db_session, session_id=session["id"], frames=frames)
    _store_evaluation_artifact(
        db_session,
        session_id=session["id"],
        evaluation_result=_evaluation_result(
            session_id=session["id"],
            drill=drill,
            phase_specs=[("descent", 0, 4, "knees")],
        ),
    )

    response = client.post(
        f"/api/sessions/{session['id']}/model/temporal",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert "MISSING_FUZZY_INTERPRETATION_RESULT" in payload["diagnostic_flags"]


def test_phase4f_service_uses_fuzzy_confidence_when_available(client, db_session) -> None:
    drill = _get_drill(db_session, "Bodyweight Squat")
    session_id = str(UUID("00000000-0000-0000-0000-000000000002"))
    frames = [
        _frame(session_id=session_id, frame_index=index, center_x=0.50 + (index * 0.01), center_y=0.20 + (index * 0.01))
        for index in range(5)
    ]
    pose_sequence = _pose_sequence(session_id, frames)
    evaluation_result = _evaluation_result(
        session_id=session_id,
        drill=drill,
        phase_specs=[("descent", 0, 4, "knees")],
    )
    fuzzy_result = _fuzzy_result(
        session_id=session_id,
        drill=drill,
        phase_id="descent",
        metric_id="descent_timing_metric",
        confidence=0.30,
    )

    result = TemporalModelingService().model(
        pose_sequence=pose_sequence,
        evaluation_result=evaluation_result,
        fuzzy_result=fuzzy_result,
    )

    assert result.status == "COMPLETED"
    assert result.phase_temporal_results[0].temporal_state == "UNCERTAIN"
