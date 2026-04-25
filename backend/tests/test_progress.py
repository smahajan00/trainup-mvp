from __future__ import annotations

from sqlalchemy import select

from app.engines.perception_interface.perception_service import PerceptionService
from app.models.drill import Drill
from app.models.progress_record import ProgressRecord
from app.models.session_summary import SessionSummary
from app.schemas.session import PoseSequenceResponse


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


def _create_upload_session(client, token: str, drill: Drill) -> dict[str, str]:
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

    response = client.post(
        "/api/sessions",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


def _build_pose_sequence(session_id: str) -> PoseSequenceResponse:
    return PoseSequenceResponse(
        session_id=session_id,
        pose_model="mediapipe_pose",
        preprocessing_version="phase1_v0_1_0",
        frame_count=3,
        valid_frame_count=3,
        status="COMPLETED",
        diagnostic_flags=[],
        sequence_data=[],
        created_at=None,
    )


def test_recent_progress_endpoint_returns_empty_when_phase2_outputs_do_not_exist(
    client,
    db_session,
    monkeypatch,
) -> None:
    token = _register_user(client, full_name="Progress User", email="progress@example.com")
    drill = _get_drill(db_session, "Defensive Stance")
    upload_session = _create_upload_session(client, token, drill)

    monkeypatch.setattr(
        PerceptionService,
        "process_uploaded_file",
        lambda self, **kwargs: _build_pose_sequence(kwargs["session_id"]),
    )

    upload_response = client.post(
        f"/api/sessions/{upload_session['id']}/upload",
        files={"file": ("defensive-stance.mp4", b"3" * 8192, "video/mp4")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert upload_response.status_code == 200

    response = client.get(
        "/api/progress/recent",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["recent_sessions"] == []
    assert payload["recent_metrics"] == []


def test_upload_does_not_create_summary_or_progress_until_phase2(
    client,
    db_session,
    monkeypatch,
) -> None:
    token = _register_user(client, full_name="Linked User", email="linked@example.com")
    drill = _get_drill(db_session, "Instep Pass")
    upload_session = _create_upload_session(client, token, drill)

    monkeypatch.setattr(
        PerceptionService,
        "process_uploaded_file",
        lambda self, **kwargs: _build_pose_sequence(kwargs["session_id"]),
    )

    response = client.post(
        f"/api/sessions/{upload_session['id']}/upload",
        files={"file": ("instep-pass.mp4", b"4" * 4096, "video/mp4")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    summary = db_session.scalar(
        select(SessionSummary).where(SessionSummary.session_id == upload_session["id"])
    )
    progress_records = list(
        db_session.scalars(
            select(ProgressRecord).where(ProgressRecord.summary_id == summary.id)
        )
    ) if summary is not None else []

    assert response.json()["pose_sequence"]["status"] == "COMPLETED"
    assert summary is None
    assert progress_records == []
