from __future__ import annotations

from sqlalchemy import select

from app.models.drill import Drill
from app.models.progress_record import ProgressRecord
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


def _create_upload_session(client, token: str, drill_id: str) -> dict[str, str]:
    response = client.post(
        "/api/sessions",
        json={"drill_id": drill_id, "input_type": "UPLOAD"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


def test_recent_progress_endpoint_returns_real_sessions_and_metrics(client, db_session) -> None:
    token = _register_user(client, full_name="Progress User", email="progress@example.com")
    drill_id = _get_drill_id(db_session, "Defensive Stance")
    upload_session = _create_upload_session(client, token, drill_id)

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
    assert len(payload["recent_sessions"]) == 1
    assert payload["recent_sessions"][0]["session_id"] == upload_session["id"]
    assert payload["recent_sessions"][0]["drill_name"] == "Defensive Stance"
    assert payload["recent_sessions"][0]["overall_accuracy"] == upload_response.json()["session_summary"]["overall_accuracy"]
    assert len(payload["recent_metrics"]) == len(
        upload_response.json()["evaluation_result"]["metric_scores"]
    )
    assert {
        metric["metric_name"] for metric in payload["recent_metrics"]
    } == set(upload_response.json()["evaluation_result"]["metric_scores"].keys())


def test_summary_and_progress_records_are_linked_to_processed_session(client, db_session) -> None:
    token = _register_user(client, full_name="Linked User", email="linked@example.com")
    drill_id = _get_drill_id(db_session, "Instep Pass")
    upload_session = _create_upload_session(client, token, drill_id)

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

    assert summary is not None
    assert summary.summary_text.startswith("Your Instep Pass session")
    assert len(progress_records) == len(response.json()["evaluation_result"]["metric_scores"])
