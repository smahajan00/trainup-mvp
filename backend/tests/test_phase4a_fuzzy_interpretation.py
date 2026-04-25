from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import select

from app.engines.fuzzy_engine.fuzzy_interpretation_contract import (
    DEFAULT_FUZZY_DEVIATION_BANDS,
    FUZZY_INTERPRETATION_VERSION,
)
from app.models.drill import Drill
from app.models.enums import ComputationStatus, SeverityLevel
from app.models.session_artifact import SessionArtifact
from app.schemas.session import (
    DeterministicEvaluationIssueResponse,
    DeterministicEvaluationResult,
    EvaluationFrameRangeResponse,
    MetricEvaluationResultResponse,
    PhaseEvaluationResultResponse,
    RankedMetricResponse,
)
from app.services.fuzzy_interpretation_service import (
    FuzzyInterpretationService,
    assign_primary_fuzzy_label,
    compute_dominant_confidence,
    compute_fuzzy_membership_scores,
    direction_aware_fuzzy_label,
)

SUPPORTED_FUZZY_CASES = (
    ("Bodyweight Squat", "knee_alignment_score", "descent", "knees"),
    ("Set Shot Form", "shooting_alignment", "release", "shooting_arm"),
    ("Dumbbell Shoulder Press", "elbow_extension", "press", "elbow"),
    ("Defensive Stance", "knee_flexion", "hold", "knees"),
    ("Instep Pass", "instep_contact_extension", "contact", "kicking_leg"),
    ("Basic Shooting Form", "shooting_contact_extension", "contact", "kicking_leg"),
)


def _register_user(client, *, email: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Phase 4A Fuzzy",
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


def _metric_result(
    *,
    metric_id: str,
    phase_id: str,
    affected_body_part: str,
    deviation: float | None = 0.18,
    issue_direction: str = "UNDER_RANGE",
    computation_status: ComputationStatus = ComputationStatus.COMPUTED,
) -> MetricEvaluationResultResponse:
    return MetricEvaluationResultResponse(
        metric_id=metric_id,
        metric_name=metric_id,
        phase_id=phase_id,
        raw_value=0.62 if computation_status is ComputationStatus.COMPUTED else None,
        unit="score",
        ideal_min=0.80,
        ideal_max=1.0,
        deviation=deviation,
        issue_direction=issue_direction,
        severity_level=SeverityLevel.MODERATE,
        normalized_score=0.62 if computation_status is ComputationStatus.COMPUTED else None,
        affected_body_part=affected_body_part,
        computation_status=computation_status,
        valid_frame_count=8 if computation_status is ComputationStatus.COMPUTED else 0,
        formula_version="phase0_v0_1_0",
        diagnostic_flags=[],
    )


def _evaluation_result(
    *,
    session_id: str,
    drill: Drill,
    metric_result: MetricEvaluationResultResponse,
) -> DeterministicEvaluationResult:
    issue = DeterministicEvaluationIssueResponse(
        phase_id=metric_result.phase_id,
        metric_id=metric_result.metric_id,
        metric_name=metric_result.metric_name,
        severity_level=metric_result.severity_level,
        affected_body_part=metric_result.affected_body_part,
        deviation=metric_result.deviation or 0.0,
        issue_direction=metric_result.issue_direction,
        computation_status=metric_result.computation_status,
        diagnostic_flags=[],
    )
    return DeterministicEvaluationResult(
        status="COMPLETED",
        session_id=UUID(session_id),
        sport_id=drill.sport_id,
        skill_level="BEGINNER",
        drill_id=drill.id,
        phase_results=[
            PhaseEvaluationResultResponse(
                phase_id=metric_result.phase_id,
                frame_range=EvaluationFrameRangeResponse(
                    phase_id=metric_result.phase_id,
                    start_frame_index=0,
                    end_frame_index=2,
                    start_timestamp_ms=0.0,
                    end_timestamp_ms=66.6,
                ),
                metric_results=[metric_result],
                phase_score=0.62,
                phase_severity=metric_result.severity_level,
                detected_issues=[issue],
            )
        ],
        overall_score=0.62,
        overall_severity=metric_result.severity_level,
        detected_issues=[issue],
        strongest_metrics=[
            RankedMetricResponse(
                phase_id=metric_result.phase_id,
                metric_id=metric_result.metric_id or metric_result.metric_name,
                metric_name=metric_result.metric_name,
                score=0.62,
            )
        ],
        weakest_metrics=[
            RankedMetricResponse(
                phase_id=metric_result.phase_id,
                metric_id=metric_result.metric_id or metric_result.metric_name,
                metric_name=metric_result.metric_name,
                score=0.62,
            )
        ],
        diagnostic_flags=[],
    )


def _store_evaluation_artifact(
    db_session,
    *,
    session_id: str,
    drill: Drill,
    metric_result: MetricEvaluationResultResponse,
) -> DeterministicEvaluationResult:
    evaluation_result = _evaluation_result(
        session_id=session_id,
        drill=drill,
        metric_result=metric_result,
    )
    db_session.add(
        SessionArtifact(
            session_id=UUID(session_id),
            artifact_type="evaluation_result",
            payload_json=evaluation_result.model_dump(mode="json"),
        )
    )
    db_session.commit()
    return evaluation_result


@pytest.mark.parametrize(
    ("deviation", "expected_label"),
    [
        (0.0, "IDEAL"),
        (0.08, "SLIGHTLY_OFF"),
        (0.18, "MODERATELY_OFF"),
        (0.30, "STRONGLY_OFF"),
    ],
)
def test_phase4a_membership_label_assignment(
    deviation: float,
    expected_label: str,
) -> None:
    scores = compute_fuzzy_membership_scores(
        deviation,
        DEFAULT_FUZZY_DEVIATION_BANDS,
    )

    assert set(scores) == {
        "IDEAL",
        "SLIGHTLY_OFF",
        "MODERATELY_OFF",
        "STRONGLY_OFF",
    }
    confidence = compute_dominant_confidence(scores)
    assert confidence == max(scores.values())
    assert 0.0 <= confidence <= 1.0
    assert assign_primary_fuzzy_label(scores) == expected_label


def test_phase4a_direction_aware_labels() -> None:
    assert (
        direction_aware_fuzzy_label(
            primary_label="SLIGHTLY_OFF",
            issue_direction="UNDER_RANGE",
        )
        == "SLIGHTLY_LOW"
    )
    assert (
        direction_aware_fuzzy_label(
            primary_label="STRONGLY_OFF",
            issue_direction="OVER_RANGE",
        )
        == "STRONGLY_HIGH"
    )
    assert (
        direction_aware_fuzzy_label(
            primary_label="MODERATELY_OFF",
            issue_direction="NONE",
        )
        == "IDEAL"
    )


def test_phase4a_dominant_confidence_matches_membership_peak() -> None:
    scores = {
        "IDEAL": 0.1,
        "SLIGHTLY_OFF": 0.45,
        "MODERATELY_OFF": 0.8,
        "STRONGLY_OFF": 0.2,
    }

    confidence = compute_dominant_confidence(scores)

    assert confidence == 0.8
    assert 0.0 <= confidence <= 1.0


def test_phase4a_missing_membership_scores_fail_safely(
    db_session,
    monkeypatch,
) -> None:
    drill = _get_drill(db_session, "Bodyweight Squat")
    evaluation_result = _evaluation_result(
        session_id=str(UUID(int=3)),
        drill=drill,
        metric_result=_metric_result(
            metric_id="knee_alignment_score",
            phase_id="descent",
            affected_body_part="knees",
        ),
    )

    monkeypatch.setattr(
        "app.services.fuzzy_interpretation_service.compute_fuzzy_membership_scores",
        lambda deviation, bands: {},
    )

    result = FuzzyInterpretationService().interpret(
        evaluation_result=evaluation_result,
    )

    assert result.fuzzy_metric_results[0].primary_fuzzy_label == "NOT_INTERPRETABLE"
    assert result.fuzzy_metric_results[0].dominant_label_confidence is None
    assert "MISSING_MEMBERSHIP_SCORES" in result.diagnostic_flags


def test_phase4a_not_computable_metrics_are_not_interpretable(db_session) -> None:
    drill = _get_drill(db_session, "Bodyweight Squat")
    evaluation_result = _evaluation_result(
        session_id=str(UUID(int=1)),
        drill=drill,
        metric_result=_metric_result(
            metric_id="knee_alignment_score",
            phase_id="descent",
            affected_body_part="knees",
            deviation=None,
            computation_status=ComputationStatus.NOT_COMPUTABLE,
        ),
    )

    result = FuzzyInterpretationService().interpret(
        evaluation_result=evaluation_result,
    )

    assert result.status == "NO_INTERPRETABLE_METRICS"
    assert result.fuzzy_metric_results[0].primary_fuzzy_label == "NOT_INTERPRETABLE"
    assert result.fuzzy_metric_results[0].direction_aware_label == "NOT_INTERPRETABLE"
    assert result.fuzzy_metric_results[0].dominant_label_confidence is None
    assert "METRIC_NOT_COMPUTABLE" in result.diagnostic_flags


def test_phase4a_service_can_be_disabled(db_session) -> None:
    drill = _get_drill(db_session, "Bodyweight Squat")
    evaluation_result = _evaluation_result(
        session_id=str(UUID(int=2)),
        drill=drill,
        metric_result=_metric_result(
            metric_id="knee_alignment_score",
            phase_id="descent",
            affected_body_part="knees",
        ),
    )

    result = FuzzyInterpretationService(enabled=False).interpret(
        evaluation_result=evaluation_result,
    )

    assert result.status == "DISABLED"
    assert result.fuzzy_metric_results == []
    assert result.diagnostic_flags == ["FUZZY_INTERPRETATION_DISABLED"]


@pytest.mark.parametrize(
    ("drill_name", "metric_id", "phase_id", "affected_body_part"),
    SUPPORTED_FUZZY_CASES,
)
def test_phase4a_persists_fuzzy_interpretation_for_supported_drills(
    client,
    db_session,
    drill_name: str,
    metric_id: str,
    phase_id: str,
    affected_body_part: str,
) -> None:
    token = _register_user(client, email=f"phase4a-{metric_id}@example.com")
    drill = _get_drill(db_session, drill_name)
    session = _create_session(client, token, drill)
    _store_evaluation_artifact(
        db_session,
        session_id=session["id"],
        drill=drill,
        metric_result=_metric_result(
            metric_id=metric_id,
            phase_id=phase_id,
            affected_body_part=affected_body_part,
        ),
    )

    response = client.post(
        f"/api/sessions/{session['id']}/interpret/fuzzy",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "fuzzy_version",
        "status",
        "session_id",
        "drill_id",
        "sport_id",
        "skill_level",
        "fuzzy_metric_results",
        "fuzzy_summary",
        "diagnostic_flags",
        "created_at",
    }
    assert payload["fuzzy_version"] == FUZZY_INTERPRETATION_VERSION
    assert payload["status"] == "COMPLETED"
    fuzzy_metric = payload["fuzzy_metric_results"][0]
    assert fuzzy_metric["metric_id"] == metric_id
    assert fuzzy_metric["primary_fuzzy_label"] == "MODERATELY_OFF"
    assert fuzzy_metric["direction_aware_label"] == "MODERATELY_LOW"
    assert fuzzy_metric["membership_scores"]["MODERATELY_OFF"] == 1.0
    assert fuzzy_metric["dominant_label_confidence"] == 1.0
    assert 0.0 <= fuzzy_metric["dominant_label_confidence"] <= 1.0

    artifact = db_session.scalar(
        select(SessionArtifact).where(
            SessionArtifact.session_id == session["id"],
            SessionArtifact.artifact_type == "fuzzy_interpretation_result",
        )
    )
    assert artifact is not None
    assert artifact.payload_json["fuzzy_version"] == FUZZY_INTERPRETATION_VERSION
    assert (
        artifact.payload_json["fuzzy_metric_results"][0]["dominant_label_confidence"]
        == 1.0
    )

    artifacts_response = client.get(
        f"/api/sessions/{session['id']}/artifacts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert artifacts_response.status_code == 200
    assert (
        artifacts_response.json()["fuzzy_interpretation_result"]["fuzzy_version"]
        == FUZZY_INTERPRETATION_VERSION
    )


def test_phase4a_missing_evaluation_artifact_fails_safely(client, db_session) -> None:
    token = _register_user(client, email="phase4a-missing@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)

    response = client.post(
        f"/api/sessions/{session['id']}/interpret/fuzzy",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "FAILED"
    assert payload["fuzzy_metric_results"] == []
    assert "EVALUATION_NOT_COMPLETED" in payload["diagnostic_flags"]
    assert "MISSING_EVALUATION_RESULT" in payload["diagnostic_flags"]


def test_phase4a_existing_feedback_flow_still_works(client, db_session) -> None:
    token = _register_user(client, email="phase4a-feedback-regression@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)
    _store_evaluation_artifact(
        db_session,
        session_id=session["id"],
        drill=drill,
        metric_result=_metric_result(
            metric_id="knee_alignment_score",
            phase_id="descent",
            affected_body_part="knees",
        ),
    )
    fuzzy_response = client.post(
        f"/api/sessions/{session['id']}/interpret/fuzzy",
        headers={"Authorization": f"Bearer {token}"},
    )
    feedback_response = client.post(
        f"/api/sessions/{session['id']}/feedback",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert fuzzy_response.status_code == 200
    assert feedback_response.status_code == 200
    assert feedback_response.json()["status"] == "COMPLETED"
    assert feedback_response.json()["prioritized_feedback_items"]
