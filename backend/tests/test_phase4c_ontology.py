from __future__ import annotations

from collections import Counter
from uuid import UUID

import pytest
from sqlalchemy import select

from app.engines.ontology_engine.ontology_contract import (
    ONTOLOGY_MAPPINGS_BY_METRIC_ID,
    PHASE2_SUPPORTED_METRIC_IDS,
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
    ONTOLOGY_REASONING_VERSION,
    PEDAGOGICAL_DECISION_VERSION,
    PedagogicalDecisionResult,
    PhaseEvaluationResultResponse,
    RankedMetricResponse,
)
from app.services.ontology_reasoning_service import OntologyReasoningService


def _register_user(client, *, email: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Phase 4C Ontology",
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


def _pedagogical_result(
    *,
    session_id: str,
    drill: Drill,
    skill_level: str,
    learning_objective: str,
) -> PedagogicalDecisionResult:
    return PedagogicalDecisionResult(
        pedagogical_version=PEDAGOGICAL_DECISION_VERSION,
        status="COMPLETED",
        session_id=UUID(session_id),
        sport_id=drill.sport_id,
        drill_id=drill.id,
        skill_level=skill_level,
        teaching_strategy="dual_focus_refinement",
        selected_focus_items=[],
        suppressed_items=[],
        tone_profile="corrective_specific",
        correction_intensity="corrective",
        learning_objective=learning_objective,
        progression_advice="Refine the movement with one clear emphasis.",
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


def test_phase4c_mapping_coverage_is_complete() -> None:
    assert len(PHASE2_SUPPORTED_METRIC_IDS) == 28
    assert set(PHASE2_SUPPORTED_METRIC_IDS) == set(ONTOLOGY_MAPPINGS_BY_METRIC_ID)
    knee_mapping = ONTOLOGY_MAPPINGS_BY_METRIC_ID["knee_alignment_score"]
    assert knee_mapping.body_part == "knee"
    assert "alignment" in knee_mapping.concepts
    depth_mapping = ONTOLOGY_MAPPINGS_BY_METRIC_ID["squat_depth"]
    assert depth_mapping.body_part == "knee"
    assert "depth" in depth_mapping.concepts


def test_phase4c_groups_multiple_metrics_into_same_concept(db_session) -> None:
    service = OntologyReasoningService()
    drill = _get_drill(db_session, "Bodyweight Squat")
    metric_results = [
        _metric_result(
            metric_id="knee_alignment_score",
            phase_id="descent",
            severity_level=SeverityLevel.SEVERE,
            affected_body_part="knee",
            deviation=0.22,
        ),
        _metric_result(
            metric_id="wrist_elbow_alignment",
            phase_id="press",
            severity_level=SeverityLevel.MODERATE,
            affected_body_part="wrist",
            deviation=0.12,
        ),
    ]
    evaluation_result = _evaluation_result(
        session_id="00000000-0000-0000-0000-000000000001",
        drill=drill,
        skill_level="INTERMEDIATE",
        metric_results=metric_results,
    )
    fuzzy_result = _fuzzy_result(
        session_id="00000000-0000-0000-0000-000000000001",
        drill=drill,
        skill_level="INTERMEDIATE",
        metric_results=metric_results,
        labels_and_confidence=[("STRONGLY_OFF", 0.85), ("MODERATELY_OFF", 0.7)],
    )

    result = service.reason(
        evaluation_result=evaluation_result,
        fuzzy_result=fuzzy_result,
    )

    assert result.status == "COMPLETED"
    assert "alignment" in result.concept_groups
    assert result.concept_groups["alignment"].metrics == [
        "knee_alignment_score",
        "wrist_elbow_alignment",
    ]
    assert result.concept_groups["alignment"].phases == ["descent", "press"]


def test_phase4c_dominant_concept_detection_uses_pedagogical_tiebreak(
    db_session,
) -> None:
    service = OntologyReasoningService()
    drill = _get_drill(db_session, "Bodyweight Squat")
    metric_results = [
        _metric_result(
            metric_id="knee_flexion",
            phase_id="descent",
            severity_level=SeverityLevel.MODERATE,
            affected_body_part="knee",
            deviation=0.11,
        ),
        _metric_result(
            metric_id="hip_stability",
            phase_id="bottom",
            severity_level=SeverityLevel.MODERATE,
            affected_body_part="hip",
            deviation=0.11,
        ),
    ]
    evaluation_result = _evaluation_result(
        session_id="00000000-0000-0000-0000-000000000002",
        drill=drill,
        skill_level="INTERMEDIATE",
        metric_results=metric_results,
    )
    fuzzy_result = _fuzzy_result(
        session_id="00000000-0000-0000-0000-000000000002",
        drill=drill,
        skill_level="INTERMEDIATE",
        metric_results=metric_results,
        labels_and_confidence=[("MODERATELY_OFF", 0.7), ("MODERATELY_OFF", 0.7)],
    )
    pedagogical_result = _pedagogical_result(
        session_id="00000000-0000-0000-0000-000000000002",
        drill=drill,
        skill_level="INTERMEDIATE",
        learning_objective="mobility",
    )

    result = service.reason(
        evaluation_result=evaluation_result,
        fuzzy_result=fuzzy_result,
        pedagogical_result=pedagogical_result,
    )

    assert result.primary_concept == "mobility"


def test_phase4c_severity_weighting_prefers_severe_issue(db_session) -> None:
    service = OntologyReasoningService()
    drill = _get_drill(db_session, "Dumbbell Shoulder Press")
    metric_results = [
        _metric_result(
            metric_id="shoulder_symmetry",
            phase_id="lockout",
            severity_level=SeverityLevel.SEVERE,
            affected_body_part="shoulder",
            deviation=0.2,
        ),
        _metric_result(
            metric_id="knee_flexion",
            phase_id="setup",
            severity_level=SeverityLevel.MODERATE,
            affected_body_part="knee",
            deviation=0.14,
        ),
    ]
    evaluation_result = _evaluation_result(
        session_id="00000000-0000-0000-0000-000000000003",
        drill=drill,
        skill_level="ADVANCED",
        metric_results=metric_results,
    )
    fuzzy_result = _fuzzy_result(
        session_id="00000000-0000-0000-0000-000000000003",
        drill=drill,
        skill_level="ADVANCED",
        metric_results=metric_results,
        labels_and_confidence=[("STRONGLY_OFF", 0.8), ("STRONGLY_OFF", 0.9)],
    )

    result = service.reason(
        evaluation_result=evaluation_result,
        fuzzy_result=fuzzy_result,
    )

    assert result.primary_concept == "alignment"


def test_phase4c_confidence_weighting_changes_priority(db_session) -> None:
    service = OntologyReasoningService()
    drill = _get_drill(db_session, "Basic Shooting Form")
    metric_results = [
        _metric_result(
            metric_id="knee_flexion",
            phase_id="load",
            severity_level=SeverityLevel.MODERATE,
            affected_body_part="knee",
            deviation=0.12,
        ),
        _metric_result(
            metric_id="hip_stability",
            phase_id="contact",
            severity_level=SeverityLevel.MODERATE,
            affected_body_part="hip",
            deviation=0.12,
        ),
    ]
    evaluation_result = _evaluation_result(
        session_id="00000000-0000-0000-0000-000000000004",
        drill=drill,
        skill_level="ADVANCED",
        metric_results=metric_results,
    )
    fuzzy_result = _fuzzy_result(
        session_id="00000000-0000-0000-0000-000000000004",
        drill=drill,
        skill_level="ADVANCED",
        metric_results=metric_results,
        labels_and_confidence=[("MODERATELY_OFF", 0.9), ("MODERATELY_OFF", 0.4)],
    )

    result = service.reason(
        evaluation_result=evaluation_result,
        fuzzy_result=fuzzy_result,
    )

    assert result.primary_concept == "depth"


def test_phase4c_missing_mapping_is_flagged_and_skipped(db_session) -> None:
    service = OntologyReasoningService()
    drill = _get_drill(db_session, "Bodyweight Squat")
    metric_results = [
        _metric_result(
            metric_id="unknown_metric",
            phase_id="descent",
            severity_level=SeverityLevel.SEVERE,
            affected_body_part="custom",
            deviation=0.3,
        )
    ]
    evaluation_result = _evaluation_result(
        session_id="00000000-0000-0000-0000-000000000005",
        drill=drill,
        skill_level="BEGINNER",
        metric_results=metric_results,
    )

    result = service.reason(
        evaluation_result=evaluation_result,
        fuzzy_result=None,
    )

    assert result.status == "NO_SIGNIFICANT_ISSUES"
    assert result.concept_groups == {}
    assert "ONTOLOGY_MAPPING_MISSING:unknown_metric" in result.diagnostic_flags


def test_phase4c_no_issue_session_returns_empty_reasoning(db_session) -> None:
    service = OntologyReasoningService()
    drill = _get_drill(db_session, "Bodyweight Squat")
    metric_results = [
        _metric_result(
            metric_id="knee_alignment_score",
            phase_id="descent",
            severity_level=SeverityLevel.MINOR,
            affected_body_part="knee",
            deviation=0.04,
        )
    ]
    evaluation_result = _evaluation_result(
        session_id="00000000-0000-0000-0000-000000000006",
        drill=drill,
        skill_level="BEGINNER",
        metric_results=metric_results,
    )

    result = service.reason(
        evaluation_result=evaluation_result,
        fuzzy_result=None,
    )

    assert result.status == "NO_SIGNIFICANT_ISSUES"
    assert result.primary_concept is None
    assert result.concept_groups == {}


def test_phase4c_missing_fuzzy_uses_base_severity_weight(db_session) -> None:
    service = OntologyReasoningService()
    drill = _get_drill(db_session, "Dumbbell Shoulder Press")
    metric_results = [
        _metric_result(
            metric_id="shoulder_symmetry",
            phase_id="lockout",
            severity_level=SeverityLevel.SEVERE,
            affected_body_part="shoulder",
            deviation=0.21,
        )
    ]
    evaluation_result = _evaluation_result(
        session_id="00000000-0000-0000-0000-000000000007",
        drill=drill,
        skill_level="ADVANCED",
        metric_results=metric_results,
    )

    result = service.reason(
        evaluation_result=evaluation_result,
        fuzzy_result=None,
    )

    assert "MISSING_FUZZY_INTERPRETATION_RESULT" in result.diagnostic_flags
    assert result.concept_groups["alignment"].total_weight == 2.0


def test_phase4c_missing_evaluation_artifact_fails_cleanly(client, db_session) -> None:
    token = _register_user(client, email="phase4c-missing-eval@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill, skill_level="BEGINNER")

    response = client.post(
        f"/api/sessions/{session['id']}/ontology",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "FAILED"
    assert "MISSING_EVALUATION_RESULT" in payload["diagnostic_flags"]


def test_phase4c_persists_and_upserts_ontology_artifact(client, db_session) -> None:
    token = _register_user(client, email="phase4c-persist@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill, skill_level="INTERMEDIATE")
    metric_results = [
        _metric_result(
            metric_id="knee_alignment_score",
            phase_id="descent",
            severity_level=SeverityLevel.SEVERE,
            affected_body_part="knee",
            deviation=0.23,
        ),
        _metric_result(
            metric_id="torso_alignment",
            phase_id="ascent",
            severity_level=SeverityLevel.MODERATE,
            affected_body_part="trunk",
            deviation=0.14,
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
        labels_and_confidence=[("STRONGLY_OFF", 0.92), ("MODERATELY_OFF", 0.67)],
    )
    pedagogical_result = _pedagogical_result(
        session_id=session["id"],
        drill=drill,
        skill_level="INTERMEDIATE",
        learning_objective="alignment",
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
        artifact_type="pedagogical_decision_result",
        payload=pedagogical_result,
    )
    db_session.commit()

    for _ in range(2):
        response = client.post(
            f"/api/sessions/{session['id']}/ontology",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["ontology_version"] == ONTOLOGY_REASONING_VERSION
        assert payload["status"] == "COMPLETED"
        assert payload["primary_concept"] == "control"

    ontology_artifacts = db_session.scalars(
        select(SessionArtifact).where(
            SessionArtifact.session_id == UUID(session["id"]),
            SessionArtifact.artifact_type == "ontology_reasoning_result",
        )
    ).all()
    assert len(ontology_artifacts) == 1

    artifacts_response = client.get(
        f"/api/sessions/{session['id']}/artifacts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert artifacts_response.status_code == 200
    artifacts_payload = artifacts_response.json()
    assert artifacts_payload["ontology_reasoning_result"]["status"] == "COMPLETED"
    assert artifacts_payload["ontology_reasoning_result"]["primary_concept"] == "control"
    assert "body_region_summary" in artifacts_payload["ontology_reasoning_result"]
