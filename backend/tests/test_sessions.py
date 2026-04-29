from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.engines.perception_interface.perception_service import PerceptionService
from app.models.drill import Drill
from app.models.enums import CameraView, SkillLevel
from app.models.feedback import Feedback
from app.models.metric_result import MetricResult
from app.models.progress_record import ProgressRecord
from app.models.session_artifact import SessionArtifact
from app.models.session_summary import SessionSummary
from app.schemas.session import (
    PoseFrameResponse,
    PoseLandmarkCoordinate,
    PoseSequenceResponse,
)
from app.services.capture_protocol_validator import CaptureProtocolValidator


def _register_user(client, *, full_name: str, email: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": full_name,
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


def _create_session(
    client,
    token: str,
    *,
    drill: Drill,
    input_type: str,
    skill_level: str = "BEGINNER",
    camera_view: str | None = None,
    dominant_side: str | None = None,
) -> dict[str, str]:
    payload = {
        "sport_id": str(drill.sport_id),
        "skill_level": skill_level,
        "drill_id": str(drill.id),
        "input_type": input_type,
    }
    if camera_view is not None:
        payload["camera_view"] = camera_view
    if dominant_side is not None:
        payload["dominant_side"] = dominant_side

    response = client.post(
        "/api/sessions",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


SUPPORTED_CAPTURE_PROTOCOL_CASES = (
    ("Bodyweight Squat", ("RIGHT_SAGITTAL", "LEFT_SAGITTAL"), "FRONTAL"),
    ("Dumbbell Shoulder Press", ("FRONTAL",), "RIGHT_SAGITTAL"),
    ("Set Shot Form", ("FRONTAL",), "RIGHT_SAGITTAL"),
    ("Defensive Stance", ("FRONTAL",), "RIGHT_SAGITTAL"),
    ("Instep Pass", ("RIGHT_SAGITTAL", "LEFT_SAGITTAL"), "FRONTAL"),
    ("Basic Shooting Form", ("RIGHT_SAGITTAL", "LEFT_SAGITTAL"), "FRONTAL"),
)


def _build_pose_sequence(
    session_id: str,
    *,
    status: str = "COMPLETED",
    frame_count: int = 2,
    valid_frame_count: int = 2,
    diagnostic_flags: list[str] | None = None,
) -> PoseSequenceResponse:
    frames: list[PoseFrameResponse] = []
    for frame_index in range(frame_count):
        frame_is_valid = frame_index < valid_frame_count
        frames.append(
            PoseFrameResponse(
                session_id=session_id,
                frame_index=frame_index,
                timestamp_ms=float(frame_index * 33.3),
                landmarks=(
                    {
                        "left_shoulder": PoseLandmarkCoordinate(
                            x=0.42 + (frame_index * 0.01),
                            y=0.18,
                            visibility=0.95,
                        ),
                        "right_shoulder": PoseLandmarkCoordinate(
                            x=0.58 + (frame_index * 0.01),
                            y=0.18,
                            visibility=0.96,
                        ),
                    }
                    if frame_is_valid
                    else {}
                ),
                frame_valid=frame_is_valid,
                diagnostic_flags=[] if frame_is_valid else ["POSE_NOT_DETECTED"],
            )
        )

    return PoseSequenceResponse(
        session_id=session_id,
        pose_model="mediapipe_pose",
        preprocessing_version="phase1_v0_1_0",
        frame_count=frame_count,
        valid_frame_count=valid_frame_count,
        status=status,
        diagnostic_flags=diagnostic_flags or [],
        sequence_data=frames,
        created_at=None,
    )


def test_create_session_success(client, db_session) -> None:
    token = _register_user(client, full_name="Jordan Carter", email="jordansession@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")

    response = client.post(
        "/api/sessions",
        json={
            "sport_id": str(drill.sport_id),
            "skill_level": "ADVANCED",
            "drill_id": str(drill.id),
            "input_type": "UPLOAD",
            "camera_view": "RIGHT_SAGITTAL",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["drill_name"] == "Bodyweight Squat"
    assert payload["sport_name"] == "Gym"
    assert payload["skill_level"] == "ADVANCED"
    assert payload["input_type"] == "UPLOAD"
    assert payload["camera_view"] == "RIGHT_SAGITTAL"
    assert payload["dominant_side"] is None
    assert payload["status"] == "ACTIVE"
    assert payload["end_time"] is None


def test_skill_level_enum_values_are_canonical() -> None:
    assert {level.value for level in SkillLevel} == {
        "BEGINNER",
        "INTERMEDIATE",
        "ADVANCED",
    }


def test_create_session_requires_explicit_skill_level(client, db_session) -> None:
    token = _register_user(client, full_name="Level Missing", email="levelmissing@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")

    response = client.post(
        "/api/sessions",
        json={
            "sport_id": str(drill.sport_id),
            "drill_id": str(drill.id),
            "input_type": "UPLOAD",
            "camera_view": "RIGHT_SAGITTAL",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_create_session_accepts_skill_level_independent_of_drill(client, db_session) -> None:
    token = _register_user(client, full_name="Advanced Squat", email="advancedsquat@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")

    response = client.post(
        "/api/sessions",
        json={
            "sport_id": str(drill.sport_id),
            "skill_level": "ADVANCED",
            "drill_id": str(drill.id),
            "input_type": "UPLOAD",
            "camera_view": "RIGHT_SAGITTAL",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["skill_level"] == "ADVANCED"


def test_create_session_invalid_dill_rejected(client) -> None:
    token = _register_user(client, full_name="Casey Brooks", email="casey@example.com")

    response = client.post(
        "/api/sessions",
        json={
            "sport_id": str(uuid4()),
            "skill_level": "BEGINNER",
            "drill_id": str(uuid4()),
            "input_type": "LIVE",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Requested drill was not found."


def test_create_session_rejects_mismatched_sport(client, db_session) -> None:
    token = _register_user(client, full_name="Alex Ford", email="sportmismatch@example.com")
    squat = _get_drill(db_session, "Bodyweight Squat")
    shot = _get_drill(db_session, "Set Shot Form")

    response = client.post(
        "/api/sessions",
        json={
            "sport_id": str(shot.sport_id),
            "skill_level": "INTERMEDIATE",
            "drill_id": str(squat.id),
            "input_type": "UPLOAD",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Requested sport does not match the requested drill."


def test_create_session_allows_auto_detect_dominant_side_for_set_shot_form(
    client,
    db_session,
) -> None:
    token = _register_user(client, full_name="Sam Price", email="dominantside@example.com")
    drill = _get_drill(db_session, "Set Shot Form")

    response = client.post(
        "/api/sessions",
        json={
            "sport_id": str(drill.sport_id),
            "skill_level": "INTERMEDIATE",
            "drill_id": str(drill.id),
            "input_type": "UPLOAD",
            "camera_view": "FRONTAL",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["drill_name"] == "Set Shot Form"
    assert payload["dominant_side"] is None


def test_get_session_owned_by_user(client, db_session) -> None:
    token = _register_user(client, full_name="Riley Stone", email="riley@example.com")
    drill = _get_drill(db_session, "Set Shot Form")
    created_session = _create_session(
        client,
        token,
        drill=drill,
        input_type="LIVE",
        camera_view="FRONTAL",
        dominant_side="RIGHT",
    )

    response = client.get(
        f"/api/sessions/{created_session['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == created_session["id"]
    assert payload["drill_name"] == "Set Shot Form"


def test_get_session_rejected_for_other_user(client, db_session) -> None:
    owner_token = _register_user(client, full_name="Owner User", email="owner@example.com")
    other_token = _register_user(client, full_name="Other User", email="other@example.com")
    drill = _get_drill(db_session, "Instep Pass")
    created_session = _create_session(client, owner_token, drill=drill, input_type="LIVE")

    response = client.get(
        f"/api/sessions/{created_session['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Requested session was not found."


def test_recent_sessions_return_most_recent_first(client, db_session) -> None:
    token = _register_user(client, full_name="Morgan Reed", email="recent@example.com")
    squat = _get_drill(db_session, "Bodyweight Squat")
    shot = _get_drill(db_session, "Set Shot Form")

    _create_session(
        client,
        token,
        drill=squat,
        input_type="UPLOAD",
        camera_view="RIGHT_SAGITTAL",
    )
    latest_session = _create_session(
        client,
        token,
        drill=shot,
        input_type="LIVE",
        camera_view="FRONTAL",
        dominant_side="RIGHT",
    )

    response = client.get(
        "/api/sessions/recent",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["id"] == latest_session["id"]
    assert payload[0]["drill_name"] == "Set Shot Form"


def test_upload_endpoint_rejects_wrong_input_type(client, db_session) -> None:
    token = _register_user(client, full_name="Avery Lane", email="uploadtype@example.com")
    drill = _get_drill(db_session, "Defensive Stance")
    live_session = _create_session(client, token, drill=drill, input_type="LIVE")

    response = client.post(
        f"/api/sessions/{live_session['id']}/upload",
        files={"file": ("stance.mp4", b"video-data", "video/mp4")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "This session does not accept uploaded media."


def test_upload_success_persists_pose_sequence(client, db_session, monkeypatch) -> None:
    token = _register_user(client, full_name="Jamie Cole", email="uploadmeta@example.com")
    drill = _get_drill(db_session, "Basic Shooting Form")
    upload_session = _create_session(
        client,
        token,
        drill=drill,
        input_type="UPLOAD",
        camera_view="RIGHT_SAGITTAL",
        dominant_side="RIGHT",
    )

    def fake_process_uploaded_file(self, **kwargs):
        return _build_pose_sequence(kwargs["session_id"])

    monkeypatch.setattr(
        PerceptionService,
        "process_uploaded_file",
        fake_process_uploaded_file,
    )

    valid_response = client.post(
        f"/api/sessions/{upload_session['id']}/upload",
        files={"file": ("shooting.mp4", b"0" * 1024, "video/mp4")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert valid_response.status_code == 200
    valid_payload = valid_response.json()
    assert valid_payload["upload_received"] is True
    assert valid_payload["validation"]["is_valid"] is True
    assert valid_payload["validation"]["errors"] == []
    assert valid_payload["capture_validation"]["is_valid"] is True
    assert valid_payload["pose_sequence"] == {
        "session_id": upload_session["id"],
        "pose_model": "mediapipe_pose",
        "preprocessing_version": "phase1_v0_1_0",
        "frame_count": 2,
        "valid_frame_count": 2,
        "status": "COMPLETED",
        "diagnostic_flags": [],
    }
    assert valid_payload["artifacts_persisted"] == ["pose_sequence"]
    assert valid_payload["next_step"] == "Pose sequence saved. Ready for deterministic evaluation."
    assert valid_payload["feedback"] == []

    invalid_response = client.post(
        f"/api/sessions/{upload_session['id']}/upload",
        files={"file": ("notes.txt", b"0" * 256, "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert invalid_response.status_code == 200
    invalid_payload = invalid_response.json()
    assert invalid_payload["upload_received"] is False
    assert invalid_payload["validation"]["is_valid"] is False
    assert (
        "Uploaded media must be a supported video file (MP4, MOV, WEBM, or MKV)."
        in invalid_payload["validation"]["errors"]
    )
    assert "pose_sequence" not in invalid_payload


def test_upload_pipeline_persists_pose_sequence_artifact(client, db_session, monkeypatch) -> None:
    token = _register_user(client, full_name="Quinn Rivera", email="artifactsave@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    upload_session = _create_session(
        client,
        token,
        drill=drill,
        input_type="UPLOAD",
        camera_view="RIGHT_SAGITTAL",
    )

    def fake_process_uploaded_file(self, **kwargs):
        return _build_pose_sequence(kwargs["session_id"], frame_count=3, valid_frame_count=2)

    monkeypatch.setattr(
        PerceptionService,
        "process_uploaded_file",
        fake_process_uploaded_file,
    )

    upload_response = client.post(
        f"/api/sessions/{upload_session['id']}/upload",
        files={"file": ("squat.mp4", b"1" * 4096, "video/mp4")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert upload_response.status_code == 200

    stored_artifacts = list(
        db_session.scalars(
            select(SessionArtifact).where(SessionArtifact.session_id == upload_session["id"])
        )
    )
    stored_feedback = list(
        db_session.scalars(
            select(Feedback).where(Feedback.session_id == upload_session["id"])
        )
    )
    stored_metric_results = list(
        db_session.scalars(
            select(MetricResult).where(MetricResult.session_id == upload_session["id"])
        )
    )
    stored_summary = db_session.scalar(
        select(SessionSummary).where(SessionSummary.session_id == upload_session["id"])
    )
    stored_progress = list(
        db_session.scalars(
            select(ProgressRecord).where(ProgressRecord.summary_id == stored_summary.id)
        )
    ) if stored_summary is not None else []
    assert len(stored_artifacts) == 1
    assert {artifact.artifact_type for artifact in stored_artifacts} == {"pose_sequence"}
    assert stored_feedback == []
    assert stored_metric_results == []
    assert stored_summary is None
    assert stored_progress == []
    assert upload_response.json()["pose_sequence"]["valid_frame_count"] == 2

    artifacts_response = client.get(
        f"/api/sessions/{upload_session['id']}/artifacts",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert artifacts_response.status_code == 200
    payload = artifacts_response.json()
    assert len(payload["artifacts"]) == 1
    assert payload["artifacts"][0]["artifact_type"] == "pose_sequence"
    assert payload["pose_sequence"]["session_id"] == upload_session["id"]
    assert payload["pose_sequence"]["pose_model"] == "mediapipe_pose"
    assert payload["pose_sequence"]["preprocessing_version"] == "phase1_v0_1_0"
    assert payload["pose_sequence"]["frame_count"] == 3
    assert payload["pose_sequence"]["valid_frame_count"] == 2
    assert len(payload["pose_sequence"]["sequence_data"]) == 3
    assert payload["feedback"] == []


def test_reprocess_replaces_existing_pose_sequence_artifact(client, db_session, monkeypatch) -> None:
    token = _register_user(client, full_name="Taylor Bloom", email="reprocess@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    upload_session = _create_session(
        client,
        token,
        drill=drill,
        input_type="UPLOAD",
        camera_view="RIGHT_SAGITTAL",
    )

    def fake_first_process(self, **kwargs):
        return _build_pose_sequence(kwargs["session_id"], frame_count=2, valid_frame_count=2)

    def fake_second_process(self, **kwargs):
        return _build_pose_sequence(
            kwargs["session_id"],
            status="INSUFFICIENT_DATA",
            frame_count=4,
            valid_frame_count=0,
            diagnostic_flags=["ZERO_VALID_FRAMES"],
        )

    monkeypatch.setattr(
        PerceptionService,
        "process_uploaded_file",
        fake_first_process,
    )
    first_response = client.post(
        f"/api/sessions/{upload_session['id']}/upload",
        files={"file": ("squat-a.mp4", b"1" * 4096, "video/mp4")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first_response.status_code == 200

    monkeypatch.setattr(
        PerceptionService,
        "process_uploaded_file",
        fake_second_process,
    )
    second_response = client.post(
        f"/api/sessions/{upload_session['id']}/upload",
        files={"file": ("squat-b.mp4", b"2" * 8192, "video/mp4")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second_response.status_code == 200
    second_payload = second_response.json()

    stored_artifacts = list(
        db_session.scalars(
            select(SessionArtifact).where(SessionArtifact.session_id == upload_session["id"])
        )
    )
    stored_feedback = list(
        db_session.scalars(
            select(Feedback).where(Feedback.session_id == upload_session["id"])
        )
    )
    stored_metric_results = list(
        db_session.scalars(
            select(MetricResult).where(MetricResult.session_id == upload_session["id"])
        )
    )
    stored_summary = db_session.scalar(
        select(SessionSummary).where(SessionSummary.session_id == upload_session["id"])
    )
    stored_progress = list(
        db_session.scalars(
            select(ProgressRecord).where(ProgressRecord.summary_id == stored_summary.id)
        )
    ) if stored_summary is not None else []

    assert len(stored_artifacts) == 1
    assert stored_artifacts[0].artifact_type == "pose_sequence"
    assert stored_feedback == []
    assert stored_metric_results == []
    assert stored_summary is None
    assert stored_progress == []
    assert second_payload["pose_sequence"]["status"] == "INSUFFICIENT_DATA"
    assert second_payload["pose_sequence"]["valid_frame_count"] == 0
    assert second_payload["pose_sequence"]["diagnostic_flags"] == ["ZERO_VALID_FRAMES"]


def test_get_session_artifacts_rejected_for_other_user(client, db_session) -> None:
    owner_token = _register_user(client, full_name="Owner Upload", email="ownerupload@example.com")
    other_token = _register_user(client, full_name="Other Upload", email="otherupload@example.com")
    drill = _get_drill(db_session, "Set Shot Form")
    upload_session = _create_session(
        client,
        owner_token,
        drill=drill,
        input_type="UPLOAD",
        camera_view="FRONTAL",
        dominant_side="RIGHT",
    )

    client.post(
        f"/api/sessions/{upload_session['id']}/upload",
        files={"file": ("shot.mp4", b"1" * 2048, "video/mp4")},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    response = client.get(
        f"/api/sessions/{upload_session['id']}/artifacts",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Requested session was not found."


def test_get_session_artifacts_includes_null_artifact_fields(client, db_session) -> None:
    token = _register_user(client, full_name="Artifact Shape", email="artifactshape@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    upload_session = _create_session(
        client,
        token,
        drill=drill,
        input_type="UPLOAD",
        camera_view="RIGHT_SAGITTAL",
    )

    response = client.get(
        f"/api/sessions/{upload_session['id']}/artifacts",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) >= {
        "artifacts",
        "pose_sequence",
        "perception_result",
        "cognition_result",
        "evaluation_result",
        "feedback_result",
        "llm_feedback_result",
        "session_summary",
        "feedback",
    }
    assert payload["pose_sequence"] is None
    assert payload["evaluation_result"] is None
    assert payload["feedback_result"] is None
    assert payload["llm_feedback_result"] is None
    assert payload["feedback"] == []


def test_upload_handles_unreadable_video(client, db_session, monkeypatch) -> None:
    token = _register_user(client, full_name="Noah Reed", email="unreadable@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    upload_session = _create_session(
        client,
        token,
        drill=drill,
        input_type="UPLOAD",
        camera_view="RIGHT_SAGITTAL",
    )

    def fake_process_uploaded_file(self, **kwargs):
        return _build_pose_sequence(
            kwargs["session_id"],
            status="FAILED",
            frame_count=0,
            valid_frame_count=0,
            diagnostic_flags=["VIDEO_UNREADABLE"],
        )

    monkeypatch.setattr(
        PerceptionService,
        "process_uploaded_file",
        fake_process_uploaded_file,
    )

    response = client.post(
        f"/api/sessions/{upload_session['id']}/upload",
        files={"file": ("broken.mp4", b"broken-video", "video/mp4")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["upload_received"] is True
    assert payload["pose_sequence"]["status"] == "FAILED"
    assert payload["pose_sequence"]["diagnostic_flags"] == ["VIDEO_UNREADABLE"]
    assert payload["next_step"] == "Pose extraction failed. Upload a different clip and try again."


def test_upload_handles_zero_valid_frames(client, db_session, monkeypatch) -> None:
    token = _register_user(client, full_name="Maya Hart", email="zerovalid@example.com")
    drill = _get_drill(db_session, "Set Shot Form")
    upload_session = _create_session(
        client,
        token,
        drill=drill,
        input_type="UPLOAD",
        camera_view="FRONTAL",
        dominant_side="LEFT",
    )

    def fake_process_uploaded_file(self, **kwargs):
        return _build_pose_sequence(
            kwargs["session_id"],
            status="INSUFFICIENT_DATA",
            frame_count=5,
            valid_frame_count=0,
            diagnostic_flags=["ZERO_VALID_FRAMES"],
        )

    monkeypatch.setattr(
        PerceptionService,
        "process_uploaded_file",
        fake_process_uploaded_file,
    )

    response = client.post(
        f"/api/sessions/{upload_session['id']}/upload",
        files={"file": ("shot.mp4", b"0" * 2048, "video/mp4")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["pose_sequence"]["status"] == "INSUFFICIENT_DATA"
    assert payload["pose_sequence"]["frame_count"] == 5
    assert payload["pose_sequence"]["valid_frame_count"] == 0
    assert payload["pose_sequence"]["diagnostic_flags"] == ["ZERO_VALID_FRAMES"]
    assert (
        payload["next_step"]
        == "Pose sequence saved, but the clip needs more usable pose data."
    )


def test_live_start_works_for_live_session(client, db_session) -> None:
    token = _register_user(client, full_name="Dakota Mills", email="livestart@example.com")
    drill = _get_drill(db_session, "Dumbbell Shoulder Press")
    live_session = _create_session(client, token, drill=drill, input_type="LIVE")

    response = client.post(
        f"/api/sessions/{live_session['id']}/live/start",
        json={
            "camera_permission_granted": True,
            "lighting_ready": True,
            "framing_ready": True,
            "space_ready": True,
            "client_ready": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["started"] is True
    assert payload["readiness"]["camera_ready"] is True


def test_live_end_updates_status(client, db_session) -> None:
    token = _register_user(client, full_name="Skyler Dean", email="liveend@example.com")
    drill = _get_drill(db_session, "Instep Pass")
    live_session = _create_session(client, token, drill=drill, input_type="LIVE")

    response = client.post(
        f"/api/sessions/{live_session['id']}/live/end",
        json={"final_status": "COMPLETED"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert payload["end_time"] is not None


def test_frame_batch_scaffold_accepts_valid_payload(client, db_session) -> None:
    token = _register_user(client, full_name="Harper Quinn", email="framebatch@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    live_session = _create_session(
        client,
        token,
        drill=drill,
        input_type="LIVE",
        camera_view="RIGHT_SAGITTAL",
    )

    response = client.post(
        f"/api/sessions/{live_session['id']}/live/frame-batch",
        json={
            "frame_count": 3,
            "timestamps": [0.0, 0.033, 0.066],
            "client_ready": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["frame_count"] == 3


@pytest.mark.parametrize(
    ("drill_name", "valid_views", "invalid_view"),
    SUPPORTED_CAPTURE_PROTOCOL_CASES,
)
def test_capture_protocol_configured_for_supported_drills(
    db_session,
    drill_name: str,
    valid_views: tuple[str, ...],
    invalid_view: str,
) -> None:
    drill = _get_drill(db_session, drill_name)
    capture_protocol = (drill.reference_payload or {}).get("capture_protocol")

    assert isinstance(capture_protocol, dict)
    assert capture_protocol["required"] is True
    assert set(capture_protocol["allowed_camera_views"]) == set(valid_views)

    validator = CaptureProtocolValidator()
    for valid_view in valid_views:
        result = validator.validate(
            drill=drill,
            actual_view=CameraView(valid_view),
        )
        assert result.is_valid is True
        assert result.reason_code == "CAPTURE_PROTOCOL_VALID"

    invalid_result = validator.validate(
        drill=drill,
        actual_view=CameraView(invalid_view),
    )
    assert invalid_result.is_valid is False
    assert invalid_result.reason_code == "CAPTURE_VIEW_MISMATCH"


def test_upload_capture_validation_rejects_incompatible_view(client, db_session) -> None:
    token = _register_user(client, full_name="Ari Cole", email="captureview@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    upload_session = _create_session(
        client,
        token,
        drill=drill,
        input_type="UPLOAD",
        camera_view="FRONTAL",
    )

    response = client.post(
        f"/api/sessions/{upload_session['id']}/upload",
        files={"file": ("squat.mp4", b"1" * 4096, "video/mp4")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["upload_received"] is False
    assert payload["capture_validation"]["is_valid"] is False
    assert payload["capture_validation"]["reason_code"] == "CAPTURE_VIEW_MISMATCH"
    assert payload["capture_validation"]["expected_view"] == "RIGHT_SAGITTAL"
    assert payload["capture_validation"]["actual_view"] == "FRONTAL"


def test_capture_validation_rejects_before_pose_extraction(
    client,
    db_session,
    monkeypatch,
) -> None:
    token = _register_user(client, full_name="Jordan Vale", email="precheck@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    upload_session = _create_session(
        client,
        token,
        drill=drill,
        input_type="UPLOAD",
        camera_view="FRONTAL",
    )
    extractor_called = False

    def fake_process_uploaded_file(self, **kwargs):
        nonlocal extractor_called
        extractor_called = True
        return _build_pose_sequence(kwargs["session_id"])

    monkeypatch.setattr(
        PerceptionService,
        "process_uploaded_file",
        fake_process_uploaded_file,
    )

    response = client.post(
        f"/api/sessions/{upload_session['id']}/upload",
        files={"file": ("squat.mp4", b"1" * 1024, "video/mp4")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert extractor_called is False
    payload = response.json()
    assert payload["upload_received"] is False
    assert payload["capture_validation"]["reason_code"] == "CAPTURE_VIEW_MISMATCH"
    assert payload["artifacts_persisted"] == []


def test_temporary_video_file_is_deleted_after_processing() -> None:
    service = PerceptionService()
    temp_path: Path | None = None

    with service._temporary_video_file(
        file_name="clip.mp4",
        content_type="video/mp4",
        file_bytes=b"video-bytes",
    ) as video_path:
        temp_path = video_path
        assert temp_path.exists() is True
        assert temp_path.read_bytes() == b"video-bytes"

    assert temp_path is not None
    assert temp_path.exists() is False
