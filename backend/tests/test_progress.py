from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.engines.perception_interface.perception_service import PerceptionService
from app.models.drill import Drill
from app.models.enums import SessionStatus
from app.models.progress_record import ProgressRecord
from app.models.session_summary import SessionSummary
from app.models.training_session import TrainingSession
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


def _create_completed_summary(
    client,
    db_session,
    token: str,
    drill: Drill,
    *,
    days_ago: int,
    score: float,
    status: SessionStatus = SessionStatus.COMPLETED,
) -> dict[str, str]:
    upload_session = _create_upload_session(client, token, drill)
    training_session = db_session.scalar(
        select(TrainingSession).where(TrainingSession.id == upload_session["id"])
    )
    assert training_session is not None
    training_session.status = status
    training_session.start_time = datetime.now(UTC) - timedelta(days=days_ago)
    training_session.end_time = training_session.start_time + timedelta(minutes=2)
    db_session.add(
        SessionSummary(
            session_id=training_session.id,
            summary_text=f"Score {score:.0f} summary",
            overall_accuracy=Decimal(str(score)),
            strengths={"metrics": []},
            weaknesses={"issues": []},
            recommendations={"actions": []},
        )
    )
    db_session.commit()
    return upload_session


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
    assert payload["total_analyzed_sessions"] == 0


def test_recent_progress_range_aggregates_are_not_limited_by_recent_window(
    client,
    db_session,
) -> None:
    token = _register_user(
        client,
        full_name="Range User",
        email="progress-range@example.com",
    )
    drill = _get_drill(db_session, "Defensive Stance")

    _create_completed_summary(client, db_session, token, drill, days_ago=1, score=80)
    _create_completed_summary(client, db_session, token, drill, days_ago=3, score=70)
    _create_completed_summary(client, db_session, token, drill, days_ago=14, score=60)
    _create_completed_summary(client, db_session, token, drill, days_ago=45, score=50)
    _create_completed_summary(
        client,
        db_session,
        token,
        drill,
        days_ago=2,
        score=95,
        status=SessionStatus.ABORTED,
    )
    _create_upload_session(client, token, drill)

    weekly_response = client.get(
        "/api/progress/recent?range=weekly&session_limit=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    monthly_response = client.get(
        "/api/progress/recent?range=monthly&session_limit=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    all_time_response = client.get(
        "/api/progress/recent?range=all_time&session_limit=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    compatible_response = client.get(
        "/api/progress/recent?session_limit=2",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert weekly_response.status_code == 200
    weekly_payload = weekly_response.json()
    assert weekly_payload["selected_range"] == "weekly"
    assert weekly_payload["total_analyzed_sessions"] == 2
    assert weekly_payload["average_score"] == 75.0
    assert weekly_payload["best_score"] == 80.0
    assert len(weekly_payload["recent_sessions"]) == 1

    assert monthly_response.status_code == 200
    monthly_payload = monthly_response.json()
    assert monthly_payload["selected_range"] == "monthly"
    assert monthly_payload["total_analyzed_sessions"] == 3
    assert monthly_payload["average_score"] == 70.0
    assert monthly_payload["best_score"] == 80.0

    assert all_time_response.status_code == 200
    all_time_payload = all_time_response.json()
    assert all_time_payload["selected_range"] == "all_time"
    assert all_time_payload["total_analyzed_sessions"] == 4
    assert all_time_payload["average_score"] == 65.0
    assert all_time_payload["best_score"] == 80.0

    assert compatible_response.status_code == 200
    compatible_payload = compatible_response.json()
    assert compatible_payload["selected_range"] == "all_time"
    assert compatible_payload["total_analyzed_sessions"] == 4
    assert len(compatible_payload["recent_sessions"]) == 2


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
