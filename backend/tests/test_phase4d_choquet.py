from __future__ import annotations

from collections import Counter
from uuid import UUID

import pytest
from sqlalchemy import select

from app.engines.aggregation_engine.choquet_contract import (
    CHOQUET_VERSION,
    build_capacity,
    choquet_integral,
    validate_capacity,
)
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
    OntologyReasoningResult,
    PhaseEvaluationResultResponse,
    RankedMetricResponse,
)
from app.services.choquet_aggregation_service import ChoquetAggregationService
from app.services.ontology_reasoning_service import OntologyReasoningService


def _register_user(client, *, email: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Phase 4D Choquet",
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
    drill: Drill,
    *,
    skill_level: str,
) -> dict[str, str]:
    capture_protocol = (drill.reference_payload or {}).get("capture_protocol", {})
    allowed_views = capture_protocol.get("allowed_camera_views", [])
    camera_view = capture_protocol.get("canonical_view") or (
        allowed_views[0] if allowed_views else None
    )
    payload = {
        "sport_id": str(drill.sport_id),
        "skill_level": skill_level,
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
    severity_level: SeverityLevel,
    affected_body_part: str,
    deviation: float,
    computation_status: ComputationStatus = ComputationStatus.COMPUTED,
    issue_direction: str = "UNDER_RANGE",
) -> MetricEvaluationResultResponse:
    return MetricEvaluationResultResponse(
        metric_id=metric_id,
        metric_name=metric_id,
        phase_id=phase_id,
        raw_value=0.6 if computation_status is ComputationStatus.COMPUTED else None,
        unit="score",
        ideal_min=0.8 if computation_status is ComputationStatus.COMPUTED else None,
        ideal_max=1.0 if computation_status is ComputationStatus.COMPUTED else None,
        deviation=deviation if computation_status is ComputationStatus.COMPUTED else None,
        issue_direction=issue_direction,
        severity_level=severity_level,
        normalized_score=0.6 if computation_status is ComputationStatus.COMPUTED else None,
        affected_body_part=affected_body_part,
        computation_status=computation_status,
        valid_frame_count=10,
        formula_version="phase0_v0_1_0",
        diagnostic_flags=[],
    )


def _evaluation_result(
    *,
    session_id: str,
    drill: Drill,
    skill_level: str,
    metric_results: list[MetricEvaluationResultResponse],
) -> DeterministicEvaluationResult:
    phase_results: list[PhaseEvaluationResultResponse] = []
    detected_issues: list[DeterministicEvaluationIssueResponse] = []
    severity_rank = {
        SeverityLevel.MINOR: 0,
        SeverityLevel.MODERATE: 1,
        SeverityLevel.SEVERE: 2,
    }
    for index, metric in enumerate(metric_results):
        issue = DeterministicEvaluationIssueResponse(
            phase_id=metric.phase_id,
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
                phase_id=metric.phase_id,
                frame_range=EvaluationFrameRangeResponse(
                    phase_id=metric.phase_id,
                    start_frame_index=index,
                    end_frame_index=index + 2,
                    start_timestamp_ms=float(index * 33.3),
                    end_timestamp_ms=float((index + 2) * 33.3),
                ),
                metric_results=[metric],
                phase_score=0.6,
                phase_severity=metric.severity_level,
                detected_issues=[issue],
            )
        )

    overall_severity = max(
        (metric.severity_level for metric in metric_results),
        key=lambda severity: severity_rank[severity],
        default=SeverityLevel.MINOR,
    )
    weakest_metric = metric_results[0] if metric_results else None
    return DeterministicEvaluationResult(
        status="COMPLETED",
        session_id=UUID(session_id),
        sport_id=drill.sport_id,
        skill_level=skill_level,
        drill_id=drill.id,
        phase_results=phase_results,
        overall_score=0.64,
        overall_severity=overall_severity,
        detected_issues=detected_issues,
        strongest_metrics=[
            RankedMetricResponse(
                phase_id="setup",
                metric_id="posture_accuracy",
                metric_name="posture_accuracy",
                score=0.91,
            )
        ],
        weakest_metrics=(
            [
                RankedMetricResponse(
                    phase_id=weakest_metric.phase_id,
                    metric_id=weakest_metric.metric_id or weakest_metric.metric_name,
                    metric_name=weakest_metric.metric_name,
                    score=0.58,
                )
            ]
            if weakest_metric is not None
            else []
        ),
        diagnostic_flags=[],
    )


def _membership_scores(primary_label: str, confidence: float) -> dict[str, float]:
    scores = {
        "IDEAL": 0.05,
        "SLIGHTLY_OFF": 0.1,
        "MODERATELY_OFF": 0.15,
        "STRONGLY_OFF": 0.2,
    }
    scores[primary_label] = confidence
    return scores


def _direction_aware_label(primary_label: str, issue_direction: str) -> str:
    if primary_label == "IDEAL" or issue_direction == "NONE":
        return "IDEAL"
    if issue_direction == "UNDER_RANGE":
        return primary_label.replace("_OFF", "_LOW")
    return primary_label.replace("_OFF", "_HIGH")


def _fuzzy_result(
    *,
    session_id: str,
    drill: Drill,
    skill_level: str,
    metric_results: list[MetricEvaluationResultResponse],
    labels_and_confidence: list[tuple[str, float]],
) -> FuzzyInterpretationResult:
    fuzzy_metrics: list[FuzzyMetricInterpretationResponse] = []
    counts: Counter[str] = Counter()
    for metric, (label, confidence) in zip(
        metric_results,
        labels_and_confidence,
        strict=True,
    ):
        counts[label] += 1
        fuzzy_metrics.append(
            FuzzyMetricInterpretationResponse(
                metric_id=metric.metric_id,
                metric_name=metric.metric_name,
                phase_id=metric.phase_id,
                computation_status=metric.computation_status,
                deviation=metric.deviation,
                issue_direction=metric.issue_direction,
                severity_level=metric.severity_level,
                affected_body_part=metric.affected_body_part,
                primary_fuzzy_label=label,
                membership_scores=_membership_scores(label, confidence),
                dominant_label_confidence=confidence,
                direction_aware_label=_direction_aware_label(
                    label,
                    metric.issue_direction,
                ),
                diagnostic_flags=[],
            )
        )

    dominant_label = max(
        ("STRONGLY_OFF", "MODERATELY_OFF", "SLIGHTLY_OFF", "IDEAL"),
        key=lambda label: counts[label],
    )
    return FuzzyInterpretationResult(
        status="COMPLETED",
        session_id=UUID(session_id),
        drill_id=drill.id,
        sport_id=drill.sport_id,
        skill_level=skill_level,
        fuzzy_metric_results=fuzzy_metrics,
        fuzzy_summary=FuzzySummaryResponse(
            ideal_count=counts["IDEAL"],
            slightly_off_count=counts["SLIGHTLY_OFF"],
            moderately_off_count=counts["MODERATELY_OFF"],
            strongly_off_count=counts["STRONGLY_OFF"],
            not_interpretable_count=counts["NOT_INTERPRETABLE"],
            interpretable_metric_count=len(fuzzy_metrics),
            dominant_fuzzy_label=dominant_label,
            top_concern_areas=[metric_results[0].affected_body_part] if metric_results else [],
        ),
        diagnostic_flags=[],
    )


def _store_artifact(
    db_session,
    *,
    session_id: str,
    artifact_type: str,
    payload,
) -> None:
    db_session.add(
        SessionArtifact(
            session_id=UUID(session_id),
            artifact_type=artifact_type,
            payload_json=payload.model_dump(mode="json"),
        )
    )


def test_phase4d_choquet_integral_empty_vector_returns_zero() -> None:
    assert choquet_integral(values={}, capacity={frozenset(): 0.0}) == 0.0


def test_phase4d_choquet_integral_single_value_returns_value() -> None:
    capacity = build_capacity(
        elements=["a"],
        singleton_weights={"a": 1.0},
        synergy_bonus=0.0,
    )
    assert choquet_integral(values={"a": 0.7}, capacity=capacity) == 0.7


def test_phase4d_choquet_integral_two_value_known_result() -> None:
    capacity = {
        frozenset(): 0.0,
        frozenset({"a"}): 0.3,
        frozenset({"b"}): 0.4,
        frozenset({"a", "b"}): 1.0,
    }
    validate_capacity(capacity=capacity, universe=frozenset({"a", "b"}))
    assert choquet_integral(values={"a": 0.2, "b": 0.7}, capacity=capacity) == 0.4


def test_phase4d_choquet_integral_equal_values_returns_same_value() -> None:
    capacity = build_capacity(
        elements=["a", "b"],
        singleton_weights={"a": 0.5, "b": 0.5},
        synergy_bonus=0.15,
    )
    assert choquet_integral(values={"a": 0.5, "b": 0.5}, capacity=capacity) == 0.5


def test_phase4d_validate_capacity_rejects_invalid_boundary() -> None:
    invalid_capacity = {
        frozenset(): 0.1,
        frozenset({"a"}): 1.0,
    }
    with pytest.raises(ValueError, match="g\\(empty\\)=0"):
        validate_capacity(capacity=invalid_capacity, universe=frozenset({"a"}))


def test_phase4d_validate_capacity_rejects_non_monotonic_capacity() -> None:
    invalid_capacity = {
        frozenset(): 0.0,
        frozenset({"a"}): 0.7,
        frozenset({"b"}): 0.4,
        frozenset({"c"}): 0.3,
        frozenset({"a", "b"}): 0.6,
        frozenset({"a", "c"}): 0.8,
        frozenset({"b", "c"}): 0.7,
        frozenset({"a", "b", "c"}): 1.0,
    }
    with pytest.raises(ValueError, match="not monotonic"):
        validate_capacity(
            capacity=invalid_capacity,
            universe=frozenset({"a", "b", "c"}),
        )


def test_phase4d_interacting_concepts_score_above_mean(db_session) -> None:
    choquet_service = ChoquetAggregationService()
    ontology_service = OntologyReasoningService()
    drill = _get_drill(db_session, "Bodyweight Squat")
    metric_results = [
        _metric_result(
            metric_id="knee_flexion",
            phase_id="descent",
            severity_level=SeverityLevel.SEVERE,
            affected_body_part="knee",
            deviation=0.18,
        ),
        _metric_result(
            metric_id="repetition_consistency",
            phase_id="ascent",
            severity_level=SeverityLevel.MODERATE,
            affected_body_part="knee",
            deviation=0.11,
        ),
    ]
    evaluation_result = _evaluation_result(
        session_id="00000000-0000-0000-0000-000000000201",
        drill=drill,
        skill_level="INTERMEDIATE",
        metric_results=metric_results,
    )
    fuzzy_result = _fuzzy_result(
        session_id="00000000-0000-0000-0000-000000000201",
        drill=drill,
        skill_level="INTERMEDIATE",
        metric_results=metric_results,
        labels_and_confidence=[("STRONGLY_OFF", 0.9), ("MODERATELY_OFF", 0.8)],
    )
    ontology_result = ontology_service.reason(
        evaluation_result=evaluation_result,
        fuzzy_result=fuzzy_result,
    )

    result = choquet_service.aggregate(
        evaluation_result=evaluation_result,
        ontology_result=ontology_result,
        fuzzy_result=fuzzy_result,
    )

    lower_body_control = result.concept_aggregation["lower_body_control"]
    mean_score = sum(lower_body_control.input_values.values()) / len(
        lower_body_control.input_values
    )
    assert lower_body_control.interaction_detected is True
    assert lower_body_control.choquet_score > mean_score


def test_phase4d_no_issue_session_returns_clean_empty_result(db_session) -> None:
    choquet_service = ChoquetAggregationService()
    ontology_service = OntologyReasoningService()
    drill = _get_drill(db_session, "Bodyweight Squat")
    metric_results = [
        _metric_result(
            metric_id="knee_alignment_score",
            phase_id="descent",
            severity_level=SeverityLevel.MINOR,
            affected_body_part="knee",
            deviation=0.03,
        )
    ]
    evaluation_result = _evaluation_result(
        session_id="00000000-0000-0000-0000-000000000202",
        drill=drill,
        skill_level="BEGINNER",
        metric_results=metric_results,
    )
    ontology_result = ontology_service.reason(
        evaluation_result=evaluation_result,
        fuzzy_result=None,
    )

    result = choquet_service.aggregate(
        evaluation_result=evaluation_result,
        ontology_result=ontology_result,
        fuzzy_result=None,
    )

    assert result.status == "NO_ACTIONABLE_ISSUES"
    assert result.concept_aggregation == {}
    assert result.body_region_aggregation == {}
    assert result.overall_choquet_score == 0.0


def test_phase4d_missing_fuzzy_still_aggregates_safely(db_session) -> None:
    choquet_service = ChoquetAggregationService()
    ontology_service = OntologyReasoningService()
    drill = _get_drill(db_session, "Dumbbell Shoulder Press")
    metric_results = [
        _metric_result(
            metric_id="shoulder_symmetry",
            phase_id="lockout",
            severity_level=SeverityLevel.SEVERE,
            affected_body_part="shoulder",
            deviation=0.21,
        ),
        _metric_result(
            metric_id="elbow_extension",
            phase_id="press",
            severity_level=SeverityLevel.MODERATE,
            affected_body_part="elbow",
            deviation=0.12,
        ),
    ]
    evaluation_result = _evaluation_result(
        session_id="00000000-0000-0000-0000-000000000203",
        drill=drill,
        skill_level="ADVANCED",
        metric_results=metric_results,
    )
    ontology_result = ontology_service.reason(
        evaluation_result=evaluation_result,
        fuzzy_result=None,
    )

    result = choquet_service.aggregate(
        evaluation_result=evaluation_result,
        ontology_result=ontology_result,
        fuzzy_result=None,
    )

    assert result.status == "COMPLETED"
    assert "MISSING_FUZZY_INTERPRETATION_RESULT" in result.diagnostic_flags
    assert result.overall_choquet_score > 0


def test_phase4d_missing_ontology_artifact_fails_cleanly(client, db_session) -> None:
    token = _register_user(client, email="phase4d-missing-ontology@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill, skill_level="BEGINNER")
    evaluation_result = _evaluation_result(
        session_id=session["id"],
        drill=drill,
        skill_level="BEGINNER",
        metric_results=[
            _metric_result(
                metric_id="knee_alignment_score",
                phase_id="descent",
                severity_level=SeverityLevel.SEVERE,
                affected_body_part="knee",
                deviation=0.23,
            )
        ],
    )
    _store_artifact(
        db_session,
        session_id=session["id"],
        artifact_type="evaluation_result",
        payload=evaluation_result,
    )
    db_session.commit()

    response = client.post(
        f"/api/sessions/{session['id']}/aggregate/choquet",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "FAILED"
    assert "MISSING_ONTOLOGY_REASONING_RESULT" in payload["diagnostic_flags"]


def test_phase4d_persists_and_upserts_choquet_artifact(client, db_session) -> None:
    token = _register_user(client, email="phase4d-persist@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill, skill_level="INTERMEDIATE")
    metric_results = [
        _metric_result(
            metric_id="knee_flexion",
            phase_id="descent",
            severity_level=SeverityLevel.SEVERE,
            affected_body_part="knee",
            deviation=0.19,
        ),
        _metric_result(
            metric_id="repetition_consistency",
            phase_id="ascent",
            severity_level=SeverityLevel.MODERATE,
            affected_body_part="knee",
            deviation=0.11,
        ),
    ]
    evaluation_result = _evaluation_result(
        session_id=session["id"],
        drill=drill,
        skill_level="INTERMEDIATE",
        metric_results=metric_results,
    )
    fuzzy_result = _fuzzy_result(
        session_id=session["id"],
        drill=drill,
        skill_level="INTERMEDIATE",
        metric_results=metric_results,
        labels_and_confidence=[("STRONGLY_OFF", 0.92), ("MODERATELY_OFF", 0.75)],
    )
    ontology_result = OntologyReasoningService().reason(
        evaluation_result=evaluation_result,
        fuzzy_result=fuzzy_result,
    )
    _store_artifact(
        db_session,
        session_id=session["id"],
        artifact_type="evaluation_result",
        payload=evaluation_result,
    )
    _store_artifact(
        db_session,
        session_id=session["id"],
        artifact_type="fuzzy_interpretation_result",
        payload=fuzzy_result,
    )
    _store_artifact(
        db_session,
        session_id=session["id"],
        artifact_type="ontology_reasoning_result",
        payload=ontology_result,
    )
    db_session.commit()

    for _ in range(2):
        response = client.post(
            f"/api/sessions/{session['id']}/aggregate/choquet",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["choquet_version"] == CHOQUET_VERSION
        assert payload["status"] == "COMPLETED"
        assert payload["dominant_interaction_group"] == "lower_body_control"

    choquet_artifacts = db_session.scalars(
        select(SessionArtifact).where(
            SessionArtifact.session_id == UUID(session["id"]),
            SessionArtifact.artifact_type == "choquet_aggregation_result",
        )
    ).all()
    assert len(choquet_artifacts) == 1

    artifacts_response = client.get(
        f"/api/sessions/{session['id']}/artifacts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert artifacts_response.status_code == 200
    artifacts_payload = artifacts_response.json()
    assert artifacts_payload["choquet_aggregation_result"]["status"] == "COMPLETED"
    assert (
        artifacts_payload["choquet_aggregation_result"]["dominant_interaction_group"]
        == "lower_body_control"
    )
