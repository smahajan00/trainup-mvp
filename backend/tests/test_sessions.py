from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select

from app.models.drill import Drill
from app.models.feedback import Feedback
from app.models.progress_record import ProgressRecord
from app.models.session_artifact import SessionArtifact
from app.models.session_summary import SessionSummary


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


def _get_drill_id(db_session, drill_name: str) -> str:
    drill = db_session.scalar(select(Drill).where(Drill.drill_name == drill_name))
    assert drill is not None
    return str(drill.id)


def _create_session(client, token: str, *, drill_id: str, input_type: str) -> dict[str, str]:
    response = client.post(
        "/api/sessions",
        json={"drill_id": drill_id, "input_type": input_type},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


def test_create_session_success(client, db_session) -> None:
    token = _register_user(client, full_name="Jordan Carter", email="jordansession@example.com")
    drill_id = _get_drill_id(db_session, "Bodyweight Squat")

    response = client.post(
        "/api/sessions",
        json={"drill_id": drill_id, "input_type": "UPLOAD"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["drill_name"] == "Bodyweight Squat"
    assert payload["sport_name"] == "Gym"
    assert payload["input_type"] == "UPLOAD"
    assert payload["status"] == "ACTIVE"
    assert payload["end_time"] is None


def test_create_session_invalid_dill_rejected(client) -> None:
    token = _register_user(client, full_name="Casey Brooks", email="casey@example.com")

    response = client.post(
        "/api/sessions",
        json={"drill_id": str(uuid4()), "input_type": "LIVE"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Requested drill was not found."


def test_get_session_owned_by_user(client, db_session) -> None:
    token = _register_user(client, full_name="Riley Stone", email="riley@example.com")
    drill_id = _get_drill_id(db_session, "Set Shot Form")
    created_session = _create_session(client, token, drill_id=drill_id, input_type="LIVE")

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
    drill_id = _get_drill_id(db_session, "Instep Pass")
    created_session = _create_session(client, owner_token, drill_id=drill_id, input_type="LIVE")

    response = client.get(
        f"/api/sessions/{created_session['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Requested session was not found."


def test_recent_sessions_return_most_recent_first(client, db_session) -> None:
    token = _register_user(client, full_name="Morgan Reed", email="recent@example.com")
    squat_id = _get_drill_id(db_session, "Bodyweight Squat")
    shot_id = _get_drill_id(db_session, "Set Shot Form")

    _create_session(client, token, drill_id=squat_id, input_type="UPLOAD")
    latest_session = _create_session(client, token, drill_id=shot_id, input_type="LIVE")

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
    drill_id = _get_drill_id(db_session, "Defensive Stance")
    live_session = _create_session(client, token, drill_id=drill_id, input_type="LIVE")

    response = client.post(
        f"/api/sessions/{live_session['id']}/upload",
        files={"file": ("stance.mp4", b"video-data", "video/mp4")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "This session does not accept uploaded media."


def test_upload_validation_accepts_and_rejects_metadata(client, db_session) -> None:
    token = _register_user(client, full_name="Jamie Cole", email="uploadmeta@example.com")
    drill_id = _get_drill_id(db_session, "Basic Shooting Form")
    upload_session = _create_session(client, token, drill_id=drill_id, input_type="UPLOAD")

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
    assert set(valid_payload["perception_result"].keys()) == {
        "source_type",
        "file_metadata",
        "processing_summary",
        "keypoint_series",
        "derived_motion_features",
    }
    assert valid_payload["perception_result"]["processing_summary"]["processing_mode"] == "scaffold"
    assert valid_payload["perception_result"]["source_type"] == "upload"
    assert valid_payload["perception_result"]["processing_summary"]["frame_count"] >= 48
    assert len(valid_payload["perception_result"]["keypoint_series"]) > 0
    assert set(valid_payload["cognition_result"].keys()) == {
        "analysis_mode",
        "session_id",
        "drill_id",
        "processing_readiness",
        "derived_metrics",
        "diagnostic_flags",
    }
    assert valid_payload["cognition_result"]["analysis_mode"] == "scaffold"
    assert set(valid_payload["cognition_result"]["derived_metrics"].keys()) == {
        "frame_consistency_score",
        "coverage_score",
        "motion_stability_score",
        "payload_completeness_score",
    }
    assert set(valid_payload["evaluation_result"].keys()) == {
        "evaluation_mode",
        "session_id",
        "drill_id",
        "drill_name",
        "evaluator_name",
        "metric_scores",
        "issues",
        "summary_flags",
        "feedback_count",
    }
    assert valid_payload["evaluation_result"]["evaluation_mode"] == "deterministic_scaffold"
    assert valid_payload["evaluation_result"]["drill_name"] == "Basic Shooting Form"
    assert (
        len(valid_payload["feedback"])
        == valid_payload["evaluation_result"]["feedback_count"]
        == len(valid_payload["evaluation_result"]["issues"])
    )
    metric_scores = valid_payload["evaluation_result"]["metric_scores"]
    expected_accuracy = round(
        (sum(metric_scores.values()) / len(metric_scores)) * 100,
        2,
    )
    assert valid_payload["session_summary"]["session_id"] == upload_session["id"]
    assert valid_payload["session_summary"]["overall_accuracy"] == expected_accuracy
    assert valid_payload["session_summary"]["summary_text"].startswith(
        "Your Basic Shooting Form session"
    )
    assert "metrics" in valid_payload["session_summary"]["strengths"]
    assert "issues" in valid_payload["session_summary"]["weaknesses"]
    assert "actions" in valid_payload["session_summary"]["recommendations"]
    assert valid_payload["artifacts_persisted"] == [
        "perception_payload",
        "cognition_result",
        "evaluation_result",
    ]

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
    assert "perception_result" not in invalid_payload
    assert "cognition_result" not in invalid_payload


def test_upload_pipeline_persists_artifacts(client, db_session) -> None:
    token = _register_user(client, full_name="Quinn Rivera", email="artifactsave@example.com")
    drill_id = _get_drill_id(db_session, "Bodyweight Squat")
    upload_session = _create_session(client, token, drill_id=drill_id, input_type="UPLOAD")

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
    stored_summary = db_session.scalar(
        select(SessionSummary).where(SessionSummary.session_id == upload_session["id"])
    )
    stored_progress = list(
        db_session.scalars(
            select(ProgressRecord).where(ProgressRecord.summary_id == stored_summary.id)
        )
    ) if stored_summary is not None else []
    assert len(stored_artifacts) == 3
    assert {artifact.artifact_type for artifact in stored_artifacts} == {
        "perception_payload",
        "cognition_result",
        "evaluation_result",
    }
    assert len(stored_feedback) == upload_response.json()["evaluation_result"]["feedback_count"]
    assert stored_summary is not None
    assert float(stored_summary.overall_accuracy) == upload_response.json()["session_summary"]["overall_accuracy"]
    assert len(stored_progress) == len(upload_response.json()["evaluation_result"]["metric_scores"])

    artifacts_response = client.get(
        f"/api/sessions/{upload_session['id']}/artifacts",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert artifacts_response.status_code == 200
    payload = artifacts_response.json()
    assert len(payload["artifacts"]) == 3
    assert payload["perception_result"]["processing_summary"]["processing_mode"] == "scaffold"
    assert payload["cognition_result"]["analysis_mode"] == "scaffold"
    assert payload["evaluation_result"]["evaluation_mode"] == "deterministic_scaffold"
    assert payload["session_summary"]["session_id"] == upload_session["id"]
    assert payload["cognition_result"]["diagnostic_flags"][0] == "Clip review is ready."
    assert len(payload["feedback"]) == payload["evaluation_result"]["feedback_count"]


def test_feedback_rows_are_replaced_on_reprocess(client, db_session) -> None:
    token = _register_user(client, full_name="Taylor Bloom", email="reprocess@example.com")
    drill_id = _get_drill_id(db_session, "Bodyweight Squat")
    upload_session = _create_session(client, token, drill_id=drill_id, input_type="UPLOAD")

    first_response = client.post(
        f"/api/sessions/{upload_session['id']}/upload",
        files={"file": ("squat-a.mp4", b"1" * 4096, "video/mp4")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first_response.status_code == 200
    first_payload = first_response.json()

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
    stored_summary = db_session.scalar(
        select(SessionSummary).where(SessionSummary.session_id == upload_session["id"])
    )
    stored_progress = list(
        db_session.scalars(
            select(ProgressRecord).where(ProgressRecord.summary_id == stored_summary.id)
        )
    ) if stored_summary is not None else []

    assert len(stored_artifacts) == 3
    assert len(stored_feedback) == second_payload["evaluation_result"]["feedback_count"]
    assert stored_summary is not None
    assert len(stored_progress) == len(second_payload["evaluation_result"]["metric_scores"])
    assert len(stored_feedback) <= max(
        first_payload["evaluation_result"]["feedback_count"],
        second_payload["evaluation_result"]["feedback_count"],
    )
    assert {artifact.artifact_type for artifact in stored_artifacts} == {
        "perception_payload",
        "cognition_result",
        "evaluation_result",
    }


def test_get_session_artifacts_rejected_for_other_user(client, db_session) -> None:
    owner_token = _register_user(client, full_name="Owner Upload", email="ownerupload@example.com")
    other_token = _register_user(client, full_name="Other Upload", email="otherupload@example.com")
    drill_id = _get_drill_id(db_session, "Set Shot Form")
    upload_session = _create_session(client, owner_token, drill_id=drill_id, input_type="UPLOAD")

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


def test_live_start_works_for_live_session(client, db_session) -> None:
    token = _register_user(client, full_name="Dakota Mills", email="livestart@example.com")
    drill_id = _get_drill_id(db_session, "Dumbbell Shoulder Press")
    live_session = _create_session(client, token, drill_id=drill_id, input_type="LIVE")

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
    drill_id = _get_drill_id(db_session, "Instep Pass")
    live_session = _create_session(client, token, drill_id=drill_id, input_type="LIVE")

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
    drill_id = _get_drill_id(db_session, "Bodyweight Squat")
    live_session = _create_session(client, token, drill_id=drill_id, input_type="LIVE")

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
