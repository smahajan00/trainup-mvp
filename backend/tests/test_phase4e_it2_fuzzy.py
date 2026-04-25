from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import select

from app.engines.fuzzy_engine.it2_fuzzy_contract import (
    DEFAULT_IT2_UNCERTAINTY_CONFIG,
    IT2_FUZZY_VERSION,
)
from app.models.drill import Drill
from app.models.enums import ComputationStatus, SeverityLevel
from app.models.session_artifact import SessionArtifact
from app.schemas.session import (
    FuzzyInterpretationResult,
    FuzzyMetricInterpretationResponse,
    FuzzySummaryResponse,
)
from app.services.it2_fuzzy_interpretation_service import (
    IT2FuzzyInterpretationService,
    assign_primary_interval_label,
    assign_uncertainty_category,
    compute_interval_memberships,
    compute_uncertainty_width,
)

SUPPORTED_IT2_CASES = (
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
            "full_name": "Phase 4E IT2",
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


def _membership_scores(primary_label: str, confidence: float) -> dict[str, float]:
    scores = {
        "IDEAL": 0.04,
        "SLIGHTLY_OFF": 0.08,
        "MODERATELY_OFF": 0.12,
        "STRONGLY_OFF": 0.16,
    }
    scores[primary_label] = confidence
    return scores


def _fuzzy_result(
    *,
    session_id: str,
    drill: Drill,
    metric_id: str,
    phase_id: str,
    affected_body_part: str,
    primary_label: str = "MODERATELY_OFF",
    confidence: float | None = 0.82,
    computation_status: ComputationStatus = ComputationStatus.COMPUTED,
    diagnostic_flags: list[str] | None = None,
) -> FuzzyInterpretationResult:
    diagnostic_flags = diagnostic_flags or []
    metric = FuzzyMetricInterpretationResponse(
        metric_id=metric_id,
        metric_name=metric_id,
        phase_id=phase_id,
        computation_status=computation_status,
        deviation=0.18 if computation_status is ComputationStatus.COMPUTED else None,
        issue_direction="UNDER_RANGE",
        severity_level=SeverityLevel.MODERATE,
        affected_body_part=affected_body_part,
        primary_fuzzy_label=(
            primary_label if computation_status is ComputationStatus.COMPUTED
            else "NOT_INTERPRETABLE"
        ),
        membership_scores=(
            _membership_scores(primary_label, confidence or 0.0)
            if computation_status is ComputationStatus.COMPUTED
            else {}
        ),
        dominant_label_confidence=(
            confidence if computation_status is ComputationStatus.COMPUTED else None
        ),
        direction_aware_label=(
            primary_label.replace("_OFF", "_LOW")
            if computation_status is ComputationStatus.COMPUTED
            else "NOT_INTERPRETABLE"
        ),
        diagnostic_flags=diagnostic_flags,
    )
    return FuzzyInterpretationResult(
        fuzzy_version="phase4a_v0_1_0",
        status=(
            "COMPLETED"
            if computation_status is ComputationStatus.COMPUTED
            else "NO_INTERPRETABLE_METRICS"
        ),
        session_id=UUID(session_id),
        drill_id=drill.id,
        sport_id=drill.sport_id,
        skill_level="BEGINNER",
        fuzzy_metric_results=[metric],
        fuzzy_summary=FuzzySummaryResponse(
            ideal_count=0,
            slightly_off_count=0,
            moderately_off_count=1 if primary_label == "MODERATELY_OFF" else 0,
            strongly_off_count=1 if primary_label == "STRONGLY_OFF" else 0,
            not_interpretable_count=(
                0 if computation_status is ComputationStatus.COMPUTED else 1
            ),
            interpretable_metric_count=(
                1 if computation_status is ComputationStatus.COMPUTED else 0
            ),
            dominant_fuzzy_label=(
                primary_label if computation_status is ComputationStatus.COMPUTED
                else "NOT_INTERPRETABLE"
            ),
            top_concern_areas=[affected_body_part],
        ),
        diagnostic_flags=[],
    )


def _store_fuzzy_artifact(
    db_session,
    *,
    session_id: str,
    fuzzy_result: FuzzyInterpretationResult,
) -> None:
    db_session.add(
        SessionArtifact(
            session_id=UUID(session_id),
            artifact_type="fuzzy_interpretation_result",
            payload_json=fuzzy_result.model_dump(mode="json"),
        )
    )
    db_session.commit()


def test_phase4e_uncertainty_width_increases_with_lower_confidence() -> None:
    high_confidence = compute_uncertainty_width(
        membership_scores=_membership_scores("MODERATELY_OFF", 0.9),
        dominant_label_confidence=0.9,
        diagnostic_flags=[],
        config=DEFAULT_IT2_UNCERTAINTY_CONFIG,
    )
    low_confidence = compute_uncertainty_width(
        membership_scores=_membership_scores("MODERATELY_OFF", 0.35),
        dominant_label_confidence=0.35,
        diagnostic_flags=[],
        config=DEFAULT_IT2_UNCERTAINTY_CONFIG,
    )
    assert 0.0 <= high_confidence <= 1.0
    assert 0.0 <= low_confidence <= 1.0
    assert low_confidence > high_confidence


def test_phase4e_uncertainty_width_grows_for_ambiguity_and_diagnostics() -> None:
    baseline = compute_uncertainty_width(
        membership_scores={"IDEAL": 0.05, "SLIGHTLY_OFF": 0.1, "MODERATELY_OFF": 0.82, "STRONGLY_OFF": 0.06},
        dominant_label_confidence=0.82,
        diagnostic_flags=[],
        config=DEFAULT_IT2_UNCERTAINTY_CONFIG,
    )
    ambiguous = compute_uncertainty_width(
        membership_scores={"IDEAL": 0.05, "SLIGHTLY_OFF": 0.44, "MODERATELY_OFF": 0.46, "STRONGLY_OFF": 0.09},
        dominant_label_confidence=0.46,
        diagnostic_flags=[],
        config=DEFAULT_IT2_UNCERTAINTY_CONFIG,
    )
    diagnostic = compute_uncertainty_width(
        membership_scores={"IDEAL": 0.05, "SLIGHTLY_OFF": 0.1, "MODERATELY_OFF": 0.82, "STRONGLY_OFF": 0.06},
        dominant_label_confidence=0.82,
        diagnostic_flags=["LOW_VISIBILITY"],
        config=DEFAULT_IT2_UNCERTAINTY_CONFIG,
    )
    assert ambiguous > baseline
    assert diagnostic > baseline


def test_phase4e_interval_memberships_are_clamped() -> None:
    intervals = compute_interval_memberships(
        {"IDEAL": 0.98, "SLIGHTLY_OFF": 0.1, "MODERATELY_OFF": 0.04, "STRONGLY_OFF": 0.0},
        uncertainty_width=0.2,
    )
    assert intervals["IDEAL"].lower == 0.78
    assert intervals["IDEAL"].upper == 1.0
    for interval in intervals.values():
        assert 0.0 <= interval.lower <= 1.0
        assert 0.0 <= interval.upper <= 1.0
        assert 0.0 <= interval.width <= 1.0


def test_phase4e_uncertainty_category_assignment() -> None:
    assert (
        assign_uncertainty_category(
            computation_status=ComputationStatus.COMPUTED,
            uncertainty_width=0.08,
            config=DEFAULT_IT2_UNCERTAINTY_CONFIG,
        )
        == "LOW_UNCERTAINTY"
    )
    assert (
        assign_uncertainty_category(
            computation_status=ComputationStatus.COMPUTED,
            uncertainty_width=0.18,
            config=DEFAULT_IT2_UNCERTAINTY_CONFIG,
        )
        == "MEDIUM_UNCERTAINTY"
    )
    assert (
        assign_uncertainty_category(
            computation_status=ComputationStatus.COMPUTED,
            uncertainty_width=0.29,
            config=DEFAULT_IT2_UNCERTAINTY_CONFIG,
        )
        == "HIGH_UNCERTAINTY"
    )
    assert (
        assign_uncertainty_category(
            computation_status=ComputationStatus.NOT_COMPUTABLE,
            uncertainty_width=None,
            config=DEFAULT_IT2_UNCERTAINTY_CONFIG,
        )
        == "NOT_INTERPRETABLE"
    )


def test_phase4e_primary_interval_label_uses_interval_centers() -> None:
    intervals = compute_interval_memberships(
        {"IDEAL": 0.05, "SLIGHTLY_OFF": 0.18, "MODERATELY_OFF": 0.72, "STRONGLY_OFF": 0.22},
        uncertainty_width=0.06,
    )
    assert assign_primary_interval_label(intervals) == "MODERATELY_OFF"


def test_phase4e_not_computable_metric_is_not_interpretable(
    client,
    db_session,
) -> None:
    token = _register_user(client, email="phase4e-not-computable@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)
    fuzzy_result = _fuzzy_result(
        session_id=session["id"],
        drill=drill,
        metric_id="knee_alignment_score",
        phase_id="descent",
        affected_body_part="knees",
        computation_status=ComputationStatus.NOT_COMPUTABLE,
    )

    service = IT2FuzzyInterpretationService()
    result = service.interpret(fuzzy_result=fuzzy_result)

    assert result.status == "NO_INTERPRETABLE_METRICS"
    metric = result.it2_metric_results[0]
    assert metric.uncertainty_category == "NOT_INTERPRETABLE"
    assert metric.primary_interval_label == "NOT_INTERPRETABLE"
    assert metric.uncertainty_width is None


def test_phase4e_disabled_service_returns_structured_disabled_result(
    client,
    db_session,
) -> None:
    token = _register_user(client, email="phase4e-disabled@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)
    fuzzy_result = _fuzzy_result(
        session_id=session["id"],
        drill=drill,
        metric_id="knee_alignment_score",
        phase_id="descent",
        affected_body_part="knees",
    )

    service = IT2FuzzyInterpretationService(enabled=False)
    result = service.interpret(fuzzy_result=fuzzy_result)

    assert result.status == "DISABLED"
    assert "IT2_FUZZY_DISABLED" in result.diagnostic_flags


@pytest.mark.parametrize(
    ("drill_name", "metric_id", "phase_id", "affected_body_part"),
    SUPPORTED_IT2_CASES,
)
def test_phase4e_persists_artifact_for_supported_drills(
    client,
    db_session,
    drill_name: str,
    metric_id: str,
    phase_id: str,
    affected_body_part: str,
) -> None:
    token = _register_user(
        client,
        email=f"phase4e-{metric_id}@example.com",
    )
    drill = _get_drill(db_session, drill_name)
    session = _create_session(client, token, drill)
    _store_fuzzy_artifact(
        db_session,
        session_id=session["id"],
        fuzzy_result=_fuzzy_result(
            session_id=session["id"],
            drill=drill,
            metric_id=metric_id,
            phase_id=phase_id,
            affected_body_part=affected_body_part,
        ),
    )

    response = client.post(
        f"/api/sessions/{session['id']}/interpret/it2-fuzzy",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["it2_fuzzy_version"] == IT2_FUZZY_VERSION
    assert payload["status"] == "COMPLETED"
    assert payload["it2_metric_results"][0]["metric_id"] == metric_id
    assert 0.0 <= payload["it2_metric_results"][0]["uncertainty_width"] <= 1.0


def test_phase4e_artifact_upsert_replaces_previous_result(client, db_session) -> None:
    token = _register_user(client, email="phase4e-upsert@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)

    initial_result = _fuzzy_result(
        session_id=session["id"],
        drill=drill,
        metric_id="knee_alignment_score",
        phase_id="descent",
        affected_body_part="knees",
        confidence=0.92,
    )
    _store_fuzzy_artifact(
        db_session,
        session_id=session["id"],
        fuzzy_result=initial_result,
    )

    response = client.post(
        f"/api/sessions/{session['id']}/interpret/it2-fuzzy",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    first_width = response.json()["it2_metric_results"][0]["uncertainty_width"]

    artifact = db_session.scalar(
        select(SessionArtifact).where(
            SessionArtifact.session_id == UUID(session["id"]),
            SessionArtifact.artifact_type == "fuzzy_interpretation_result",
        )
    )
    assert artifact is not None
    artifact.payload_json = _fuzzy_result(
        session_id=session["id"],
        drill=drill,
        metric_id="knee_alignment_score",
        phase_id="descent",
        affected_body_part="knees",
        confidence=0.31,
        diagnostic_flags=["LOW_VISIBILITY"],
    ).model_dump(mode="json")
    db_session.add(artifact)
    db_session.commit()

    response = client.post(
        f"/api/sessions/{session['id']}/interpret/it2-fuzzy",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    second_width = response.json()["it2_metric_results"][0]["uncertainty_width"]
    assert second_width > first_width

    artifacts = db_session.scalars(
        select(SessionArtifact).where(
            SessionArtifact.session_id == UUID(session["id"]),
            SessionArtifact.artifact_type == "it2_fuzzy_interpretation_result",
        )
    ).all()
    assert len(artifacts) == 1


def test_phase4e_missing_fuzzy_artifact_returns_failure(client, db_session) -> None:
    token = _register_user(client, email="phase4e-missing-fuzzy@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill)

    response = client.post(
        f"/api/sessions/{session['id']}/interpret/it2-fuzzy",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "FAILED"
    assert "MISSING_FUZZY_INTERPRETATION_RESULT" in payload["diagnostic_flags"]
