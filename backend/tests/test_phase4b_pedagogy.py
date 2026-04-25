from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import select

from app.models.drill import Drill
from app.models.enums import ComputationStatus, SeverityLevel
from app.models.session_artifact import SessionArtifact
from app.schemas.session import (
    DeterministicEvaluationIssueResponse,
    DeterministicEvaluationResult,
    DeterministicFeedbackItemResponse,
    DeterministicFeedbackResult,
    EvaluationFrameRangeResponse,
    FuzzyInterpretationResult,
    FuzzyMetricInterpretationResponse,
    FuzzySummaryResponse,
    MetricEvaluationResultResponse,
    PEDAGOGICAL_DECISION_VERSION,
    PhaseEvaluationResultResponse,
    RankedMetricResponse,
)


def _register_user(client, *, email: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Phase 4B Pedagogy",
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


def _feedback_item(
    *,
    phase_id: str,
    metric_id: str,
    priority_rank: int,
    severity_level: SeverityLevel,
    affected_body_part: str,
    deviation: float,
) -> DeterministicFeedbackItemResponse:
    return DeterministicFeedbackItemResponse(
        phase_id=phase_id,
        metric_id=metric_id,
        metric_name=metric_id,
        severity_level=severity_level,
        affected_body_part=affected_body_part,
        issue_direction="UNDER_RANGE",
        issue_title=f"{metric_id} needs attention",
        coaching_cue=f"Coach {metric_id}.",
        improvement_suggestion=f"Improve {metric_id}.",
        priority_rank=priority_rank,
        deviation=deviation,
    )


def _evaluation_result(
    *,
    session_id: str,
    drill: Drill,
    skill_level: str,
    feedback_items: list[DeterministicFeedbackItemResponse],
) -> DeterministicEvaluationResult:
    phase_results = []
    detected_issues = []
    for item in feedback_items:
        issue = DeterministicEvaluationIssueResponse(
            phase_id=item.phase_id,
            metric_id=item.metric_id,
            metric_name=item.metric_name,
            severity_level=item.severity_level,
            affected_body_part=item.affected_body_part,
            deviation=item.deviation,
            issue_direction=item.issue_direction,
            computation_status=ComputationStatus.COMPUTED,
            diagnostic_flags=[],
        )
        detected_issues.append(issue)
        phase_results.append(
            PhaseEvaluationResultResponse(
                phase_id=item.phase_id,
                frame_range=EvaluationFrameRangeResponse(
                    phase_id=item.phase_id,
                    start_frame_index=max(item.priority_rank - 1, 0),
                    end_frame_index=item.priority_rank + 1,
                    start_timestamp_ms=float((item.priority_rank - 1) * 33.3),
                    end_timestamp_ms=float((item.priority_rank + 1) * 33.3),
                ),
                metric_results=[
                    MetricEvaluationResultResponse(
                        metric_id=item.metric_id,
                        metric_name=item.metric_name,
                        phase_id=item.phase_id,
                        raw_value=0.6,
                        unit="score",
                        ideal_min=0.8,
                        ideal_max=1.0,
                        deviation=item.deviation,
                        issue_direction=item.issue_direction,
                        severity_level=item.severity_level,
                        normalized_score=0.6,
                        affected_body_part=item.affected_body_part,
                        computation_status=ComputationStatus.COMPUTED,
                        valid_frame_count=10,
                        formula_version="phase0_v0_1_0",
                        diagnostic_flags=[],
                    )
                ],
                phase_score=0.6,
                phase_severity=item.severity_level,
                detected_issues=[issue],
            )
        )

    weakest_item = feedback_items[0]
    return DeterministicEvaluationResult(
        status="COMPLETED",
        session_id=UUID(session_id),
        sport_id=drill.sport_id,
        skill_level=skill_level,
        drill_id=drill.id,
        phase_results=phase_results,
        overall_score=0.64,
        overall_severity=feedback_items[0].severity_level,
        detected_issues=detected_issues,
        strongest_metrics=[
            RankedMetricResponse(
                phase_id="setup",
                metric_id="posture_accuracy",
                metric_name="posture_accuracy",
                score=0.91,
            )
        ],
        weakest_metrics=[
            RankedMetricResponse(
                phase_id=weakest_item.phase_id,
                metric_id=weakest_item.metric_id or weakest_item.metric_name,
                metric_name=weakest_item.metric_name,
                score=0.58,
            )
        ],
        diagnostic_flags=[],
    )


def _feedback_result(
    *,
    session_id: str,
    feedback_items: list[DeterministicFeedbackItemResponse],
) -> DeterministicFeedbackResult:
    return DeterministicFeedbackResult(
        status="COMPLETED",
        session_id=UUID(session_id),
        overall_feedback_summary="Top focus: keep the main issue clear and actionable.",
        prioritized_feedback_items=feedback_items,
        improvement_suggestions=[item.improvement_suggestion for item in feedback_items],
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
    feedback_items: list[DeterministicFeedbackItemResponse],
    labels_and_confidence: list[tuple[str, float]],
) -> FuzzyInterpretationResult:
    fuzzy_metrics = []
    counts = {
        "IDEAL": 0,
        "SLIGHTLY_OFF": 0,
        "MODERATELY_OFF": 0,
        "STRONGLY_OFF": 0,
        "NOT_INTERPRETABLE": 0,
    }
    for item, (label, confidence) in zip(
        feedback_items,
        labels_and_confidence,
        strict=True,
    ):
        counts[label] += 1
        fuzzy_metrics.append(
            FuzzyMetricInterpretationResponse(
                metric_id=item.metric_id,
                metric_name=item.metric_name,
                phase_id=item.phase_id,
                computation_status=ComputationStatus.COMPUTED,
                deviation=item.deviation,
                issue_direction=item.issue_direction,
                severity_level=item.severity_level,
                affected_body_part=item.affected_body_part,
                primary_fuzzy_label=label,
                membership_scores=_membership_scores(label, confidence),
                dominant_label_confidence=confidence,
                direction_aware_label=_direction_aware_label(
                    label,
                    item.issue_direction,
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
            top_concern_areas=[feedback_items[0].affected_body_part],
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


@pytest.mark.parametrize(
    ("skill_level", "expected_focus_count", "expected_tone"),
    [
        ("BEGINNER", 1, "supportive_simple"),
        ("INTERMEDIATE", 2, "corrective_specific"),
        ("ADVANCED", 3, "technical_performance"),
    ],
)
def test_phase4b_focus_selection_adapts_by_skill_level(
    client,
    db_session,
    skill_level: str,
    expected_focus_count: int,
    expected_tone: str,
) -> None:
    token = _register_user(
        client,
        email=f"phase4b-focus-{skill_level.lower()}@example.com",
    )
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill, skill_level=skill_level)
    feedback_items = [
        _feedback_item(
            phase_id="descent",
            metric_id="knee_alignment_score",
            priority_rank=1,
            severity_level=SeverityLevel.SEVERE,
            affected_body_part="knees",
            deviation=0.24,
        ),
        _feedback_item(
            phase_id="ascent",
            metric_id="torso_alignment",
            priority_rank=2,
            severity_level=SeverityLevel.MODERATE,
            affected_body_part="posture",
            deviation=0.14,
        ),
        _feedback_item(
            phase_id="setup",
            metric_id="balance_stability",
            priority_rank=3,
            severity_level=SeverityLevel.MODERATE,
            affected_body_part="hips",
            deviation=0.11,
        ),
    ]
    evaluation_result = _evaluation_result(
        session_id=session["id"],
        drill=drill,
        skill_level=skill_level,
        feedback_items=feedback_items,
    )
    feedback_result = _feedback_result(
        session_id=session["id"],
        feedback_items=feedback_items,
    )
    fuzzy_result = _fuzzy_result(
        session_id=session["id"],
        drill=drill,
        skill_level=skill_level,
        feedback_items=feedback_items,
        labels_and_confidence=[
            ("STRONGLY_OFF", 0.9),
            ("MODERATELY_OFF", 0.72),
            ("SLIGHTLY_OFF", 0.51),
        ],
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
        artifact_type="feedback_result",
        payload=feedback_result,
    )
    _store_artifact(
        db_session,
        session_id=session["id"],
        artifact_type="fuzzy_interpretation_result",
        payload=fuzzy_result,
    )
    db_session.commit()

    response = client.post(
        f"/api/sessions/{session['id']}/pedagogy",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["pedagogical_version"] == PEDAGOGICAL_DECISION_VERSION
    assert payload["status"] == "COMPLETED"
    assert len(payload["selected_focus_items"]) == expected_focus_count
    assert len(payload["suppressed_items"]) == 3 - expected_focus_count
    assert payload["tone_profile"] == expected_tone


def test_phase4b_severe_high_confidence_issue_uses_direct_correction(
    client,
    db_session,
) -> None:
    token = _register_user(client, email="phase4b-direct@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill, skill_level="BEGINNER")
    feedback_items = [
        _feedback_item(
            phase_id="descent",
            metric_id="knee_alignment_score",
            priority_rank=1,
            severity_level=SeverityLevel.SEVERE,
            affected_body_part="knees",
            deviation=0.24,
        )
    ]
    _store_artifact(
        db_session,
        session_id=session["id"],
        artifact_type="evaluation_result",
        payload=_evaluation_result(
            session_id=session["id"],
            drill=drill,
            skill_level="BEGINNER",
            feedback_items=feedback_items,
        ),
    )
    _store_artifact(
        db_session,
        session_id=session["id"],
        artifact_type="feedback_result",
        payload=_feedback_result(session_id=session["id"], feedback_items=feedback_items),
    )
    _store_artifact(
        db_session,
        session_id=session["id"],
        artifact_type="fuzzy_interpretation_result",
        payload=_fuzzy_result(
            session_id=session["id"],
            drill=drill,
            skill_level="BEGINNER",
            feedback_items=feedback_items,
            labels_and_confidence=[("STRONGLY_OFF", 0.91)],
        ),
    )
    db_session.commit()

    response = client.post(
        f"/api/sessions/{session['id']}/pedagogy",
        headers={"Authorization": f"Bearer {token}"},
    )

    payload = response.json()
    assert payload["correction_intensity"] == "direct"
    assert payload["selected_focus_items"][0]["recommended_message_style"].endswith(
        ":direct"
    )


def test_phase4b_moderate_low_confidence_issue_uses_soft_correction(
    client,
    db_session,
) -> None:
    token = _register_user(client, email="phase4b-soft@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill, skill_level="INTERMEDIATE")
    feedback_items = [
        _feedback_item(
            phase_id="ascent",
            metric_id="torso_alignment",
            priority_rank=1,
            severity_level=SeverityLevel.MODERATE,
            affected_body_part="posture",
            deviation=0.13,
        )
    ]
    _store_artifact(
        db_session,
        session_id=session["id"],
        artifact_type="evaluation_result",
        payload=_evaluation_result(
            session_id=session["id"],
            drill=drill,
            skill_level="INTERMEDIATE",
            feedback_items=feedback_items,
        ),
    )
    _store_artifact(
        db_session,
        session_id=session["id"],
        artifact_type="feedback_result",
        payload=_feedback_result(session_id=session["id"], feedback_items=feedback_items),
    )
    _store_artifact(
        db_session,
        session_id=session["id"],
        artifact_type="fuzzy_interpretation_result",
        payload=_fuzzy_result(
            session_id=session["id"],
            drill=drill,
            skill_level="INTERMEDIATE",
            feedback_items=feedback_items,
            labels_and_confidence=[("SLIGHTLY_OFF", 0.35)],
        ),
    )
    db_session.commit()

    response = client.post(
        f"/api/sessions/{session['id']}/pedagogy",
        headers={"Authorization": f"Bearer {token}"},
    )

    payload = response.json()
    assert payload["correction_intensity"] == "soft"
    assert payload["selected_focus_items"][0]["dominant_label_confidence"] == 0.35


def test_phase4b_missing_fuzzy_artifact_still_returns_basic_output(
    client,
    db_session,
) -> None:
    token = _register_user(client, email="phase4b-no-fuzzy@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill, skill_level="BEGINNER")
    feedback_items = [
        _feedback_item(
            phase_id="descent",
            metric_id="knee_alignment_score",
            priority_rank=1,
            severity_level=SeverityLevel.SEVERE,
            affected_body_part="knees",
            deviation=0.22,
        )
    ]
    _store_artifact(
        db_session,
        session_id=session["id"],
        artifact_type="evaluation_result",
        payload=_evaluation_result(
            session_id=session["id"],
            drill=drill,
            skill_level="BEGINNER",
            feedback_items=feedback_items,
        ),
    )
    _store_artifact(
        db_session,
        session_id=session["id"],
        artifact_type="feedback_result",
        payload=_feedback_result(session_id=session["id"], feedback_items=feedback_items),
    )
    db_session.commit()

    response = client.post(
        f"/api/sessions/{session['id']}/pedagogy",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert "MISSING_FUZZY_INTERPRETATION_RESULT" in payload["diagnostic_flags"]
    assert payload["selected_focus_items"][0]["fuzzy_label"] is None
    assert payload["selected_focus_items"][0]["dominant_label_confidence"] is None


def test_phase4b_persists_pedagogical_artifact(client, db_session) -> None:
    token = _register_user(client, email="phase4b-persist@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill, skill_level="ADVANCED")
    feedback_items = [
        _feedback_item(
            phase_id="descent",
            metric_id="knee_alignment_score",
            priority_rank=1,
            severity_level=SeverityLevel.SEVERE,
            affected_body_part="knees",
            deviation=0.23,
        ),
        _feedback_item(
            phase_id="ascent",
            metric_id="torso_alignment",
            priority_rank=2,
            severity_level=SeverityLevel.MODERATE,
            affected_body_part="posture",
            deviation=0.15,
        ),
    ]
    _store_artifact(
        db_session,
        session_id=session["id"],
        artifact_type="evaluation_result",
        payload=_evaluation_result(
            session_id=session["id"],
            drill=drill,
            skill_level="ADVANCED",
            feedback_items=feedback_items,
        ),
    )
    _store_artifact(
        db_session,
        session_id=session["id"],
        artifact_type="feedback_result",
        payload=_feedback_result(session_id=session["id"], feedback_items=feedback_items),
    )
    _store_artifact(
        db_session,
        session_id=session["id"],
        artifact_type="fuzzy_interpretation_result",
        payload=_fuzzy_result(
            session_id=session["id"],
            drill=drill,
            skill_level="ADVANCED",
            feedback_items=feedback_items,
            labels_and_confidence=[("STRONGLY_OFF", 0.88), ("MODERATELY_OFF", 0.68)],
        ),
    )
    db_session.commit()

    response = client.post(
        f"/api/sessions/{session['id']}/pedagogy",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "pedagogical_version",
        "status",
        "session_id",
        "sport_id",
        "drill_id",
        "skill_level",
        "teaching_strategy",
        "selected_focus_items",
        "suppressed_items",
        "tone_profile",
        "correction_intensity",
        "learning_objective",
        "progression_advice",
        "diagnostic_flags",
        "created_at",
    }

    artifact = db_session.scalar(
        select(SessionArtifact).where(
            SessionArtifact.session_id == session["id"],
            SessionArtifact.artifact_type == "pedagogical_decision_result",
        )
    )
    assert artifact is not None
    assert artifact.payload_json["pedagogical_version"] == PEDAGOGICAL_DECISION_VERSION

    artifacts_response = client.get(
        f"/api/sessions/{session['id']}/artifacts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert artifacts_response.status_code == 200
    assert (
        artifacts_response.json()["pedagogical_decision_result"][
            "pedagogical_version"
        ]
        == PEDAGOGICAL_DECISION_VERSION
    )


def test_phase4b_missing_feedback_artifact_fails_cleanly(client, db_session) -> None:
    token = _register_user(client, email="phase4b-missing-feedback@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(client, token, drill, skill_level="BEGINNER")
    feedback_items = [
        _feedback_item(
            phase_id="descent",
            metric_id="knee_alignment_score",
            priority_rank=1,
            severity_level=SeverityLevel.SEVERE,
            affected_body_part="knees",
            deviation=0.21,
        )
    ]
    _store_artifact(
        db_session,
        session_id=session["id"],
        artifact_type="evaluation_result",
        payload=_evaluation_result(
            session_id=session["id"],
            drill=drill,
            skill_level="BEGINNER",
            feedback_items=feedback_items,
        ),
    )
    db_session.commit()

    response = client.post(
        f"/api/sessions/{session['id']}/pedagogy",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "FAILED"
    assert payload["selected_focus_items"] == []
    assert "MISSING_FEEDBACK_RESULT" in payload["diagnostic_flags"]
