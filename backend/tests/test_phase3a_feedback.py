from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import select

from app.models.drill import Drill
from app.models.enums import ComputationStatus, SeverityLevel
from app.models.feedback import Feedback
from app.models.session_artifact import SessionArtifact
from app.schemas.session import (
    DeterministicEvaluationIssueResponse,
    DeterministicEvaluationResult,
    EvaluationFrameRangeResponse,
    PhaseEvaluationResultResponse,
    RankedMetricResponse,
)


SUPPORTED_FEEDBACK_CASES = (
    ("Bodyweight Squat", "posture_accuracy", "setup", "posture"),
    ("Set Shot Form", "shooting_alignment", "release", "shooting arm"),
    ("Dumbbell Shoulder Press", "elbow_extension", "press", "elbow"),
    ("Defensive Stance", "knee_flexion", "hold", "knees"),
    ("Instep Pass", "instep_contact_extension", "contact", "kicking leg"),
    ("Basic Shooting Form", "shooting_contact_extension", "contact", "kicking leg"),
)


def _register_user(client, *, email: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Phase 3A Feedback",
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


def _issue(
    *,
    phase_id: str,
    metric_id: str,
    severity_level: SeverityLevel = SeverityLevel.MODERATE,
    affected_body_part: str = "body",
    deviation: float = 0.12,
    computation_status: ComputationStatus = ComputationStatus.COMPUTED,
) -> DeterministicEvaluationIssueResponse:
    return DeterministicEvaluationIssueResponse(
        phase_id=phase_id,
        metric_id=metric_id,
        metric_name=metric_id,
        severity_level=severity_level,
        affected_body_part=affected_body_part,
        deviation=deviation,
        issue_direction="UNDER_RANGE",
        computation_status=computation_status,
        diagnostic_flags=[],
    )


def _store_evaluation_artifact(
    db_session,
    *,
    session_id: str,
    drill: Drill,
    issues: list[DeterministicEvaluationIssueResponse],
    overall_severity: SeverityLevel = SeverityLevel.SEVERE,
) -> None:
    phase_ids = list(dict.fromkeys(issue.phase_id for issue in issues)) or ["setup"]
    weakest_metric_id = (
        issues[0].metric_id or issues[0].metric_name if issues else "none"
    )
    weakest_metric_name = issues[0].metric_name if issues else "none"
    result = DeterministicEvaluationResult(
        status="COMPLETED",
        session_id=UUID(session_id),
        sport_id=drill.sport_id,
        skill_level="BEGINNER",
        drill_id=drill.id,
        phase_results=[
            PhaseEvaluationResultResponse(
                phase_id=phase_id,
                frame_range=EvaluationFrameRangeResponse(
                    phase_id=phase_id,
                    start_frame_index=0,
                    end_frame_index=1,
                    start_timestamp_ms=0.0,
                    end_timestamp_ms=33.3,
                ),
                metric_results=[],
                phase_score=0.75,
                phase_severity=SeverityLevel.MODERATE,
                detected_issues=[
                    issue for issue in issues if issue.phase_id == phase_id
                ],
            )
            for phase_id in phase_ids
        ],
        overall_score=0.72,
        overall_severity=overall_severity,
        detected_issues=issues,
        strongest_metrics=[
            RankedMetricResponse(
                phase_id=phase_ids[0],
                metric_id="posture_accuracy",
                metric_name="posture_accuracy",
                score=0.93,
            )
        ],
        weakest_metrics=[
            RankedMetricResponse(
                phase_id=phase_ids[0],
                metric_id=weakest_metric_id,
                metric_name=weakest_metric_name,
                score=0.55,
            )
        ],
        diagnostic_flags=[],
    )
    db_session.add(
        SessionArtifact(
            session_id=UUID(session_id),
            artifact_type="evaluation_result",
            payload_json=result.model_dump(mode="json"),
        )
    )
    db_session.commit()


@pytest.mark.parametrize(
    ("drill_name", "metric_id", "phase_id", "affected_body_part"),
    SUPPORTED_FEEDBACK_CASES,
)
def test_phase3a_generates_deterministic_feedback_for_all_drills(
    client,
    db_session,
    drill_name: str,
    metric_id: str,
    phase_id: str,
    affected_body_part: str,
) -> None:
    token = _register_user(client, email=f"phase3a-{metric_id}@example.com")
    drill = _get_drill(db_session, drill_name)
    session = _create_session(client, token, drill)
    _store_evaluation_artifact(
        db_session,
        session_id=session["id"],
        drill=drill,
        issues=[
            _issue(
                phase_id=phase_id,
                metric_id=metric_id,
                severity_level=SeverityLevel.MODERATE,
                affected_body_part=affected_body_part,
            )
        ],
        overall_severity=SeverityLevel.MODERATE,
    )

    response = client.post(
        f"/api/sessions/{session['id']}/feedback",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "feedback_version",
        "status",
        "session_id",
        "overall_feedback_summary",
        "prioritized_feedback_items",
        "improvement_suggestions",
        "diagnostic_flags",
        "created_at",
    }
    assert payload["feedback_version"] == "phase3a_v0_1_0"
    assert payload["status"] == "COMPLETED"
    assert payload["prioritized_feedback_items"][0]["metric_id"] == metric_id
    assert payload["prioritized_feedback_items"][0]["priority_rank"] == 1
    assert payload["prioritized_feedback_items"][0]["coaching_cue"]
    assert payload["prioritized_feedback_items"][0]["what_happened"]
    assert payload["prioritized_feedback_items"][0]["why_it_matters"]
    assert payload["prioritized_feedback_items"][0]["what_to_fix"]
    assert payload["prioritized_feedback_items"][0]["next_rep_cue"]
    assert payload["prioritized_feedback_items"][0]["simple_coaching_phrase"]
    assert payload["improvement_suggestions"]
    assert "Next focus:" in payload["overall_feedback_summary"]
    assert "Top focus:" not in payload["overall_feedback_summary"]
    assert "Main issue:" not in payload["overall_feedback_summary"]
    assert "Strongest area:" not in payload["overall_feedback_summary"]

    stored_artifact = db_session.scalar(
        select(SessionArtifact).where(
            SessionArtifact.session_id == session["id"],
            SessionArtifact.artifact_type == "feedback_result",
        )
    )
    stored_feedback = list(
        db_session.scalars(select(Feedback).where(Feedback.session_id == session["id"]))
    )
    assert stored_artifact is not None
    assert stored_artifact.payload_json["feedback_version"] == "phase3a_v0_1_0"
    assert len(stored_feedback) == 1
    assert stored_feedback[0].technique_issue == payload["prioritized_feedback_items"][0]["issue_title"]

    artifacts_response = client.get(
        f"/api/sessions/{session['id']}/artifacts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert artifacts_response.status_code == 200
    assert artifacts_response.json()["feedback_result"]["feedback_version"] == "phase3a_v0_1_0"


def test_phase3a_filters_minor_and_not_computable_issues(client, db_session) -> None:
    token = _register_user(client, email="phase3a-filter@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)
    _store_evaluation_artifact(
        db_session,
        session_id=session["id"],
        drill=drill,
        issues=[
            _issue(
                phase_id="setup",
                metric_id="posture_accuracy",
                severity_level=SeverityLevel.MINOR,
            ),
            _issue(
                phase_id="descent",
                metric_id="knee_alignment_score",
                severity_level=SeverityLevel.SEVERE,
                computation_status=ComputationStatus.NOT_COMPUTABLE,
            ),
        ],
        overall_severity=SeverityLevel.MINOR,
    )

    response = client.post(
        f"/api/sessions/{session['id']}/feedback",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "NO_ACTIONABLE_ISSUES"
    assert payload["prioritized_feedback_items"] == []
    assert "NO_ACTIONABLE_ISSUES" in payload["diagnostic_flags"]
    assert "NOT_COMPUTABLE_ISSUES_SKIPPED" in payload["diagnostic_flags"]


def test_phase3a_orders_issues_by_severity_deviation_and_phase(client, db_session) -> None:
    token = _register_user(client, email="phase3a-order@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)
    _store_evaluation_artifact(
        db_session,
        session_id=session["id"],
        drill=drill,
        issues=[
            _issue(
                phase_id="ascent",
                metric_id="torso_alignment",
                severity_level=SeverityLevel.MODERATE,
                deviation=0.40,
            ),
            _issue(
                phase_id="descent",
                metric_id="knee_alignment_score",
                severity_level=SeverityLevel.SEVERE,
                deviation=0.10,
            ),
            _issue(
                phase_id="setup",
                metric_id="posture_accuracy",
                severity_level=SeverityLevel.MODERATE,
                deviation=0.55,
            ),
        ],
    )

    response = client.post(
        f"/api/sessions/{session['id']}/feedback",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    items = response.json()["prioritized_feedback_items"]
    assert [item["metric_id"] for item in items] == [
        "knee_alignment_score",
        "posture_accuracy",
        "torso_alignment",
    ]
    assert [item["priority_rank"] for item in items] == [1, 2, 3]


def test_phase3a_unsupported_template_uses_safe_fallback(client, db_session) -> None:
    token = _register_user(client, email="phase3a-fallback@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)
    _store_evaluation_artifact(
        db_session,
        session_id=session["id"],
        drill=drill,
        issues=[_issue(phase_id="setup", metric_id="unknown_metric")],
        overall_severity=SeverityLevel.MODERATE,
    )

    response = client.post(
        f"/api/sessions/{session['id']}/feedback",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert payload["prioritized_feedback_items"][0]["issue_title"] == "Improve unknown metric"
    assert "FEEDBACK_TEMPLATE_FALLBACK:unknown_metric" in payload["diagnostic_flags"]


def test_phase3a_missing_evaluation_artifact_returns_structured_failure(
    client,
    db_session,
) -> None:
    token = _register_user(client, email="phase3a-missing@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)

    response = client.post(
        f"/api/sessions/{session['id']}/feedback",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "FAILED"
    assert payload["prioritized_feedback_items"] == []
    assert payload["diagnostic_flags"] == ["MISSING_EVALUATION_RESULT"]
