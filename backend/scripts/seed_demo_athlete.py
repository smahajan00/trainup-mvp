from __future__ import annotations

import math
import random
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.drill import Drill
from app.models.enums import (
    CameraView,
    ComputationStatus,
    DominantSide,
    InputType,
    SessionStatus,
    SeverityLevel,
    SkillLevel,
)
from app.models.feedback import Feedback
from app.models.metric_result import MetricResult
from app.models.metric_type import MetricType
from app.models.progress_record import ProgressRecord
from app.models.session_artifact import SessionArtifact
from app.models.session_summary import SessionSummary
from app.models.sport import Sport
from app.models.training_session import TrainingSession
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.session import (
    ChoquetAggregationResult,
    DeterministicEvaluationResult,
    DeterministicFeedbackResult,
    FuzzyInterpretationResult,
    IT2FuzzyInterpretationResult,
    LLMFeedbackResult,
    OntologyReasoningResult,
    PedagogicalDecisionResult,
    TemporalModelingResult,
)
from app.scripts.seed_data import seed_drills, seed_metric_types, seed_sports

DEMO_EMAIL = "demo.athlete@trainup.local"
DEMO_PASSWORD = "DemoPass123!"
DEMO_NAME = "Demo Athlete"
DEMO_SESSION_COUNT = 60
DEMO_FLAG = "SYNTHETIC_DEMO_DATA"
RNG_SEED = 20260430


@dataclass(frozen=True)
class DemoCounts:
    sessions: int = 0
    summaries: int = 0
    progress_records: int = 0
    metric_results: int = 0
    artifacts: int = 0
    feedback_rows: int = 0


CATEGORY_DETAILS: dict[str, dict[str, str]] = {
    "lower_body_control": {
        "issue_title": "Lower-body control needs reinforcement",
        "issue_label": "Lower-body control inconsistency",
        "cue": "Keep the knees tracking over the toes and stay balanced through the full rep.",
        "suggestion": "Use slower reps and hold the most difficult position for one count.",
        "body_region": "lower_body",
    },
    "balance": {
        "issue_title": "Balance fades during the drill",
        "issue_label": "Balance stability inconsistency",
        "cue": "Stay centered over the support foot before adding speed.",
        "suggestion": "Run the next set at controlled speed and reset between reps.",
        "body_region": "full_body",
    },
    "posture": {
        "issue_title": "Posture changes under fatigue",
        "issue_label": "Posture control inconsistency",
        "cue": "Keep the ribs stacked over the hips and avoid drifting out of posture.",
        "suggestion": "Start each rep with a braced trunk and finish before posture breaks down.",
        "body_region": "trunk",
    },
    "follow_through": {
        "issue_title": "Follow-through is incomplete",
        "issue_label": "Follow-through inconsistency",
        "cue": "Finish the movement path fully before resetting.",
        "suggestion": "Pause briefly at the end position so the finish is controlled.",
        "body_region": "upper_body",
    },
    "temporal_control": {
        "issue_title": "Tempo is inconsistent",
        "issue_label": "Temporal control inconsistency",
        "cue": "Use the same speed on each rep and avoid rushing the transition.",
        "suggestion": "Practice with a three-count rhythm until the timing feels repeatable.",
        "body_region": "full_body",
    },
}

METRIC_CATEGORIES = {
    "posture_accuracy": "posture",
    "torso_alignment": "posture",
    "torso_rotation_stability": "posture",
    "instep_torso_tilt": "posture",
    "knee_alignment_score": "lower_body_control",
    "hip_stability": "lower_body_control",
    "knee_flexion": "lower_body_control",
    "hip_level_stability": "lower_body_control",
    "plant_foot_alignment_ratio": "lower_body_control",
    "support_foot_distance_ratio": "lower_body_control",
    "shooting_knee_load": "lower_body_control",
    "balance_stability": "balance",
    "shooting_balance": "balance",
    "instep_follow_through_stability": "balance",
    "repetition_consistency": "temporal_control",
    "stance_width_control": "temporal_control",
    "shoulder_control": "temporal_control",
    "shooting_swing_velocity": "temporal_control",
    "elbow_extension": "follow_through",
    "wrist_elbow_alignment": "follow_through",
    "lockout_control": "follow_through",
    "shoulder_symmetry": "follow_through",
    "shooting_alignment": "follow_through",
    "elbow_angle_consistency": "follow_through",
    "instep_backswing_knee_angle": "follow_through",
    "instep_contact_extension": "follow_through",
    "shooting_contact_extension": "follow_through",
}

DRILL_FOCUS_SEQUENCE = {
    "Bodyweight Squat": ["lower_body_control", "posture", "temporal_control"],
    "Dumbbell Shoulder Press": ["follow_through", "posture", "temporal_control"],
    "Instep Pass": ["follow_through", "balance", "lower_body_control"],
    "Basic Shooting Form": ["follow_through", "balance", "temporal_control"],
    "Set Shot Form": ["follow_through", "balance", "posture"],
    "Defensive Stance": ["lower_body_control", "balance", "posture"],
}

PHASE_PREFERENCES = {
    "posture_accuracy": "setup",
    "torso_alignment": "setup",
    "torso_rotation_stability": "setup",
    "knee_alignment_score": "descent",
    "hip_stability": "descent",
    "repetition_consistency": "ascent",
    "elbow_extension": "press",
    "wrist_elbow_alignment": "press",
    "lockout_control": "lockout",
    "shoulder_symmetry": "lockout",
    "shooting_alignment": "release",
    "elbow_angle_consistency": "release",
    "shoulder_control": "set",
    "balance_stability": "follow_through",
    "stance_width_control": "setup",
    "knee_flexion": "load",
    "hip_level_stability": "load",
    "plant_foot_alignment_ratio": "setup",
    "instep_backswing_knee_angle": "backswing",
    "instep_contact_extension": "contact",
    "instep_torso_tilt": "contact",
    "instep_follow_through_stability": "follow_through",
    "support_foot_distance_ratio": "approach",
    "shooting_knee_load": "load",
    "shooting_swing_velocity": "swing",
    "shooting_contact_extension": "contact",
    "shooting_balance": "follow_through",
}


def _decimal(value: float, places: int = 4) -> Decimal:
    return Decimal(f"{value:.{places}f}")


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _score_window(index: int) -> float:
    if index < 20:
        return 0.45 + ((index / 19) * 0.18)
    if index < 40:
        return 0.58 + (((index - 20) / 19) * 0.18)
    return 0.70 + (((index - 40) / 19) * 0.17)


def _severity_for_score(score: float) -> str:
    if score < 0.60:
        return SeverityLevel.SEVERE.value
    if score < 0.74:
        return SeverityLevel.MODERATE.value
    return SeverityLevel.MINOR.value


def _fuzzy_label(score: float) -> str:
    if score >= 0.86:
        return "IDEAL"
    if score >= 0.74:
        return "SLIGHTLY_OFF"
    if score >= 0.60:
        return "MODERATELY_OFF"
    return "STRONGLY_OFF"


def _direction_label(score: float) -> str:
    if score >= 0.86:
        return "IDEAL"
    if score >= 0.74:
        return "SLIGHTLY_LOW"
    if score >= 0.60:
        return "MODERATELY_LOW"
    return "STRONGLY_LOW"


def _temporal_state(score: float, focus_category: str) -> str:
    if focus_category == "temporal_control" and score < 0.75:
        return "RUSHED"
    if score < 0.58:
        return "JERKY"
    if score < 0.72:
        return "INCOMPLETE"
    if score < 0.84:
        return "CONTROLLED"
    return "STABLE"


def _model_payload(model_cls, payload: dict[str, Any]) -> dict[str, Any]:
    return model_cls(**payload).model_dump(mode="json", exclude_none=True)


def _metric_category(metric_name: str) -> str:
    return METRIC_CATEGORIES.get(metric_name, "posture")


def _metric_phase(metric_name: str, phases: list[str], fallback_index: int) -> str:
    preferred = PHASE_PREFERENCES.get(metric_name)
    if preferred in phases:
        return preferred
    return phases[fallback_index % len(phases)] if phases else "analysis"


def _score_for_metric(
    *,
    metric_name: str,
    target_score: float,
    focus_category: str,
    progress_ratio: float,
    rng: random.Random,
) -> float:
    category = _metric_category(metric_name)
    category_pressure = (1.0 - progress_ratio) * 0.15 + 0.025
    if category == focus_category:
        return _clamp(
            target_score - category_pressure + rng.uniform(-0.035, 0.025),
            0.40,
            0.94,
        )
    return _clamp(target_score + rng.uniform(-0.045, 0.075), 0.42, 0.96)


def _target_score_for_session(index: int, drill_name: str, rng: random.Random) -> float:
    drill_offsets = {
        "Bodyweight Squat": -0.015,
        "Dumbbell Shoulder Press": 0.005,
        "Instep Pass": -0.005,
        "Basic Shooting Form": 0.000,
        "Set Shot Form": 0.010,
        "Defensive Stance": -0.010,
    }
    weak_session_penalties = {
        7: 0.08,
        18: 0.06,
        31: 0.07,
        44: 0.08,
        53: 0.05,
    }
    wave = (math.sin(index * 0.82) * 0.030) + (math.sin(index * 0.27) * 0.018)
    jitter = rng.uniform(-0.022, 0.022)
    score = (
        _score_window(index)
        + drill_offsets.get(drill_name, 0.0)
        + wave
        + jitter
        - weak_session_penalties.get(index, 0.0)
    )
    return _clamp(score, 0.42, 0.91)


def _camera_view_for_drill(drill: Drill) -> CameraView | None:
    capture_protocol = (drill.reference_payload or {}).get("capture_protocol", {})
    view = capture_protocol.get("canonical_view")
    if not view:
        allowed_views = capture_protocol.get("allowed_camera_views", [])
        view = allowed_views[0] if allowed_views else None
    return CameraView(view) if view else None


def _drill_phases(drill: Drill) -> list[str]:
    phases = (drill.reference_payload or {}).get("phases", [])
    return list(phases) if phases else ["setup", "execution", "finish"]


def _drill_metric_names(drill: Drill) -> list[str]:
    return list((drill.target_metrics or {}).get("metrics", []))


def _build_metric_payloads(
    *,
    drill: Drill,
    metric_types_by_name: dict[str, MetricType],
    session_index: int,
    target_score: float,
    focus_category: str,
    rng: random.Random,
) -> list[dict[str, Any]]:
    progress_ratio = session_index / (DEMO_SESSION_COUNT - 1)
    phases = _drill_phases(drill)
    metric_payloads: list[dict[str, Any]] = []
    for metric_index, metric_name in enumerate(_drill_metric_names(drill)):
        metric_type = metric_types_by_name[metric_name]
        score = _score_for_metric(
            metric_name=metric_name,
            target_score=target_score,
            focus_category=focus_category,
            progress_ratio=progress_ratio,
            rng=rng,
        )
        issue_threshold = 0.86
        deviation = max(0.0, issue_threshold - score)
        metric_payloads.append(
            {
                "metric_id": metric_name,
                "metric_type_id": metric_type.id,
                "metric_name": metric_name,
                "phase_id": _metric_phase(metric_name, phases, metric_index),
                "raw_value": round(score, 4),
                "unit": metric_type.metric_unit,
                "ideal_min": 0.82,
                "ideal_max": 1.0,
                "deviation": round(deviation, 4),
                "issue_direction": "UNDER_RANGE" if deviation > 0 else "NONE",
                "severity_level": _severity_for_score(score),
                "normalized_score": round(score, 4),
                "affected_body_part": CATEGORY_DETAILS[_metric_category(metric_name)][
                    "body_region"
                ],
                "computation_status": ComputationStatus.COMPUTED.value,
                "valid_frame_count": 84 + ((session_index + metric_index) % 48),
                "formula_version": "synthetic_demo_v1",
                "diagnostic_flags": [DEMO_FLAG],
            }
        )
    return metric_payloads


def _issue_from_metric(metric: dict[str, Any]) -> dict[str, Any]:
    category = _metric_category(metric["metric_name"])
    details = CATEGORY_DETAILS[category]
    return {
        "phase_id": metric["phase_id"],
        "metric_id": metric["metric_id"],
        "metric_name": metric["metric_name"],
        "severity_level": metric["severity_level"],
        "affected_body_part": metric["affected_body_part"],
        "deviation": max(float(metric["deviation"]), 0.01),
        "issue_direction": "UNDER_RANGE",
        "computation_status": ComputationStatus.COMPUTED.value,
        "diagnostic_flags": [DEMO_FLAG],
        "issue_title": details["issue_title"],
        "issue_label": details["issue_label"],
        "coaching_cue": details["cue"],
        "improvement_suggestion": details["suggestion"],
    }


def _build_evaluation_payload(
    *,
    training_session: TrainingSession,
    drill: Drill,
    sport: Sport,
    metric_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    phases = _drill_phases(drill)
    metrics_by_phase = {phase: [] for phase in phases}
    for metric in metric_payloads:
        metrics_by_phase.setdefault(metric["phase_id"], []).append(metric)

    phase_results = []
    for phase_index, phase in enumerate(metrics_by_phase):
        phase_metrics = metrics_by_phase[phase]
        phase_score = (
            sum(metric["normalized_score"] for metric in phase_metrics) / len(phase_metrics)
            if phase_metrics
            else 0.0
        )
        phase_issues = [
            _issue_from_metric(metric)
            for metric in phase_metrics
            if metric["normalized_score"] < 0.82
        ]
        start_frame = phase_index * 42
        end_frame = start_frame + 41
        phase_results.append(
            {
                "phase_id": phase,
                "frame_range": {
                    "phase_id": phase,
                    "start_frame_index": start_frame,
                    "end_frame_index": end_frame,
                    "start_timestamp_ms": float(start_frame * 33),
                    "end_timestamp_ms": float(end_frame * 33),
                    "boundary_mode": "inclusive_overlapping",
                },
                "metric_results": [
                    {
                        key: value
                        for key, value in metric.items()
                        if key != "metric_type_id"
                    }
                    for metric in phase_metrics
                ],
                "phase_score": round(phase_score, 4),
                "phase_severity": _severity_for_score(phase_score),
                "detected_issues": [
                    {
                        key: value
                        for key, value in issue.items()
                        if key not in {"issue_title", "issue_label", "coaching_cue", "improvement_suggestion"}
                    }
                    for issue in phase_issues
                ],
            }
        )

    sorted_metrics = sorted(metric_payloads, key=lambda item: item["normalized_score"])
    weakest = [
        {
            "phase_id": metric["phase_id"],
            "metric_id": metric["metric_id"],
            "metric_name": metric["metric_name"],
            "score": metric["normalized_score"],
        }
        for metric in sorted_metrics[:3]
    ]
    strongest = [
        {
            "phase_id": metric["phase_id"],
            "metric_id": metric["metric_id"],
            "metric_name": metric["metric_name"],
            "score": metric["normalized_score"],
        }
        for metric in sorted(metric_payloads, key=lambda item: item["normalized_score"], reverse=True)[
            :3
        ]
    ]
    issues = [
        {
            key: value
            for key, value in _issue_from_metric(metric).items()
            if key not in {"issue_title", "issue_label", "coaching_cue", "improvement_suggestion"}
        }
        for metric in sorted_metrics[:2]
    ]
    overall_score = sum(metric["normalized_score"] for metric in metric_payloads) / len(
        metric_payloads
    )

    return _model_payload(
        DeterministicEvaluationResult,
        {
            "evaluation_version": "synthetic_demo_phase2_v1",
            "status": "COMPLETED",
            "session_id": training_session.id,
            "sport_id": sport.id,
            "skill_level": training_session.skill_level,
            "drill_id": drill.id,
            "phase_results": phase_results,
            "overall_score": round(overall_score, 4),
            "overall_severity": _severity_for_score(overall_score),
            "detected_issues": issues,
            "strongest_metrics": strongest,
            "weakest_metrics": weakest,
            "diagnostic_flags": [DEMO_FLAG],
            "resolved_dominant_side": training_session.dominant_side,
            "dominant_side_confidence": 0.92 if training_session.dominant_side else None,
            "dominant_side_diagnostic_flags": (
                [DEMO_FLAG, "DEMO_DOMINANT_SIDE_ASSIGNED"]
                if training_session.dominant_side
                else None
            ),
        },
    )


def _build_feedback_payload(
    *,
    training_session: TrainingSession,
    weakest_metrics: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    feedback_items = []
    for priority, metric in enumerate(weakest_metrics[:2], start=1):
        issue = _issue_from_metric(metric)
        feedback_items.append(
            {
                "phase_id": issue["phase_id"],
                "metric_id": issue["metric_id"],
                "metric_name": issue["metric_name"],
                "severity_level": issue["severity_level"],
                "affected_body_part": issue["affected_body_part"],
                "issue_direction": "UNDER_RANGE",
                "issue_title": issue["issue_title"],
                "coaching_cue": issue["coaching_cue"],
                "improvement_suggestion": issue["improvement_suggestion"],
                "priority_rank": priority,
                "deviation": issue["deviation"],
            }
        )
    suggestions = [item["improvement_suggestion"] for item in feedback_items]
    summary = (
        "Synthetic demo coaching: focus on the top movement constraint while preserving the improving trend."
    )
    return (
        _model_payload(
            DeterministicFeedbackResult,
            {
                "feedback_version": "synthetic_demo_phase3_v1",
                "status": "COMPLETED",
                "session_id": training_session.id,
                "overall_feedback_summary": summary,
                "prioritized_feedback_items": feedback_items,
                "improvement_suggestions": suggestions,
                "diagnostic_flags": [DEMO_FLAG],
            },
        ),
        feedback_items,
    )


def _build_fuzzy_payload(
    *,
    training_session: TrainingSession,
    drill: Drill,
    sport: Sport,
    metric_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    fuzzy_results = []
    label_counts = {
        "IDEAL": 0,
        "SLIGHTLY_OFF": 0,
        "MODERATELY_OFF": 0,
        "STRONGLY_OFF": 0,
        "NOT_INTERPRETABLE": 0,
    }
    for metric in metric_payloads:
        score = metric["normalized_score"]
        label = _fuzzy_label(score)
        label_counts[label] += 1
        fuzzy_results.append(
            {
                "metric_id": metric["metric_id"],
                "metric_name": metric["metric_name"],
                "phase_id": metric["phase_id"],
                "computation_status": ComputationStatus.COMPUTED.value,
                "deviation": metric["deviation"],
                "issue_direction": metric["issue_direction"],
                "severity_level": metric["severity_level"],
                "affected_body_part": metric["affected_body_part"],
                "primary_fuzzy_label": label,
                "membership_scores": {
                    "IDEAL": round(_clamp(score - 0.72, 0, 1), 4),
                    "SLIGHTLY_OFF": round(_clamp(1 - abs(score - 0.78) * 4, 0, 1), 4),
                    "MODERATELY_OFF": round(_clamp(1 - abs(score - 0.65) * 4, 0, 1), 4),
                    "STRONGLY_OFF": round(_clamp(0.70 - score, 0, 1), 4),
                },
                "dominant_label_confidence": round(_clamp(0.55 + score * 0.35, 0, 1), 4),
                "direction_aware_label": _direction_label(score),
                "diagnostic_flags": [DEMO_FLAG],
            }
        )

    dominant_label = max(label_counts.items(), key=lambda item: item[1])[0]
    top_concerns = [
        CATEGORY_DETAILS[_metric_category(metric["metric_name"])]["issue_label"]
        for metric in sorted(metric_payloads, key=lambda item: item["normalized_score"])[:2]
    ]
    return _model_payload(
        FuzzyInterpretationResult,
        {
            "fuzzy_version": "synthetic_demo_phase4a_v1",
            "status": "COMPLETED",
            "session_id": training_session.id,
            "drill_id": drill.id,
            "sport_id": sport.id,
            "skill_level": training_session.skill_level,
            "fuzzy_metric_results": fuzzy_results,
            "fuzzy_summary": {
                "ideal_count": label_counts["IDEAL"],
                "slightly_off_count": label_counts["SLIGHTLY_OFF"],
                "moderately_off_count": label_counts["MODERATELY_OFF"],
                "strongly_off_count": label_counts["STRONGLY_OFF"],
                "not_interpretable_count": 0,
                "interpretable_metric_count": len(metric_payloads),
                "dominant_fuzzy_label": dominant_label,
                "top_concern_areas": top_concerns,
            },
            "diagnostic_flags": [DEMO_FLAG],
        },
    )


def _build_it2_payload(
    *,
    training_session: TrainingSession,
    drill: Drill,
    sport: Sport,
    metric_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    it2_results = []
    widths = []
    category_counts = {
        "LOW_UNCERTAINTY": 0,
        "MEDIUM_UNCERTAINTY": 0,
        "HIGH_UNCERTAINTY": 0,
        "NOT_INTERPRETABLE": 0,
    }
    for metric in metric_payloads:
        score = metric["normalized_score"]
        width = round(_clamp(0.18 - score * 0.10, 0.035, 0.14), 4)
        widths.append((width, metric))
        uncertainty = (
            "LOW_UNCERTAINTY"
            if width < 0.07
            else "MEDIUM_UNCERTAINTY"
            if width < 0.11
            else "HIGH_UNCERTAINTY"
        )
        category_counts[uncertainty] += 1
        label = _fuzzy_label(score)
        it2_results.append(
            {
                "phase_id": metric["phase_id"],
                "metric_id": metric["metric_id"],
                "metric_name": metric["metric_name"],
                "computation_status": ComputationStatus.COMPUTED.value,
                "deviation": metric["deviation"],
                "issue_direction": metric["issue_direction"],
                "severity_level": metric["severity_level"],
                "affected_body_part": metric["affected_body_part"],
                "type1_primary_label": label,
                "type1_direction_aware_label": _direction_label(score),
                "dominant_label_confidence": round(_clamp(0.58 + score * 0.30, 0, 1), 4),
                "uncertainty_width": width,
                "uncertainty_category": uncertainty,
                "interval_memberships": {
                    "IDEAL": {"lower": 0.0, "upper": round(_clamp(score, 0, 1), 4), "width": width},
                    "SLIGHTLY_OFF": {
                        "lower": round(_clamp(score - width, 0, 1), 4),
                        "upper": round(_clamp(score + width, 0, 1), 4),
                        "width": width,
                    },
                    "MODERATELY_OFF": {
                        "lower": round(_clamp(1 - score - width, 0, 1), 4),
                        "upper": round(_clamp(1 - score + width, 0, 1), 4),
                        "width": width,
                    },
                    "STRONGLY_OFF": {
                        "lower": 0.0,
                        "upper": round(_clamp(0.72 - score + width, 0, 1), 4),
                        "width": width,
                    },
                },
                "primary_interval_label": label,
                "diagnostic_flags": [DEMO_FLAG],
            }
        )
    highest_width, highest_metric = max(widths, key=lambda item: item[0])
    return _model_payload(
        IT2FuzzyInterpretationResult,
        {
            "it2_fuzzy_version": "synthetic_demo_phase4e_v1",
            "status": "COMPLETED",
            "session_id": training_session.id,
            "sport_id": sport.id,
            "drill_id": drill.id,
            "skill_level": training_session.skill_level,
            "it2_metric_results": it2_results,
            "uncertainty_summary": {
                "low_count": category_counts["LOW_UNCERTAINTY"],
                "medium_count": category_counts["MEDIUM_UNCERTAINTY"],
                "high_count": category_counts["HIGH_UNCERTAINTY"],
                "not_interpretable_count": 0,
                "average_uncertainty_width": round(
                    sum(width for width, _ in widths) / len(widths),
                    4,
                ),
                "highest_uncertainty_metric": {
                    "phase_id": highest_metric["phase_id"],
                    "metric_id": highest_metric["metric_id"],
                    "uncertainty_width": highest_width,
                },
                "summary_text": "Synthetic demo uncertainty narrows as recent scores improve.",
            },
            "diagnostic_flags": [DEMO_FLAG],
        },
    )


def _build_pedagogy_payload(
    *,
    training_session: TrainingSession,
    drill: Drill,
    sport: Sport,
    feedback_items: list[dict[str, Any]],
) -> dict[str, Any]:
    focus_items = []
    for item in feedback_items:
        focus_items.append(
            {
                "phase_id": item["phase_id"],
                "metric_id": item["metric_id"],
                "metric_name": item["metric_name"],
                "severity_level": item["severity_level"],
                "fuzzy_label": "SLIGHTLY_OFF"
                if item["severity_level"] == SeverityLevel.MINOR.value
                else "MODERATELY_OFF",
                "dominant_label_confidence": 0.78,
                "affected_body_part": item["affected_body_part"],
                "priority_rank": item["priority_rank"],
                "teaching_reason": "Synthetic demo priority selected to show dashboard coaching focus.",
                "recommended_message_style": "specific cue plus one repeatable action",
            }
        )
    return _model_payload(
        PedagogicalDecisionResult,
        {
            "pedagogical_version": "synthetic_demo_phase4b_v1",
            "status": "COMPLETED",
            "session_id": training_session.id,
            "sport_id": sport.id,
            "drill_id": drill.id,
            "skill_level": training_session.skill_level,
            "teaching_strategy": "dual_focus_refinement"
            if len(focus_items) > 1
            else "single_focus_mastery",
            "selected_focus_items": focus_items,
            "suppressed_items": [],
            "tone_profile": "supportive_simple",
            "correction_intensity": "soft"
            if focus_items[0]["severity_level"] == SeverityLevel.MINOR.value
            else "corrective",
            "learning_objective": f"Improve {focus_items[0]['metric_name'].replace('_', ' ')} with controlled repetitions.",
            "progression_advice": feedback_items[0]["improvement_suggestion"],
            "diagnostic_flags": [DEMO_FLAG],
        },
    )


def _build_ontology_payload(
    *,
    training_session: TrainingSession,
    drill: Drill,
    sport: Sport,
    focus_category: str,
    weakest_metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    details = CATEGORY_DETAILS[focus_category]
    concepts = [focus_category, "movement_quality"]
    severity_summary = {
        "severe_count": sum(
            1 for metric in weakest_metrics if metric["severity_level"] == SeverityLevel.SEVERE.value
        ),
        "moderate_count": sum(
            1
            for metric in weakest_metrics
            if metric["severity_level"] == SeverityLevel.MODERATE.value
        ),
    }
    return _model_payload(
        OntologyReasoningResult,
        {
            "ontology_version": "synthetic_demo_phase4c_v1",
            "status": "COMPLETED",
            "session_id": training_session.id,
            "sport_id": sport.id,
            "drill_id": drill.id,
            "skill_level": training_session.skill_level,
            "primary_concept": focus_category,
            "secondary_concepts": ["movement_quality", "repeatability"],
            "concept_groups": {
                focus_category: {
                    "metrics": [metric["metric_name"] for metric in weakest_metrics],
                    "phases": sorted({metric["phase_id"] for metric in weakest_metrics}),
                    "total_weight": round(
                        sum(1 - metric["normalized_score"] for metric in weakest_metrics),
                        4,
                    ),
                    "severity_summary": severity_summary,
                }
            },
            "body_region_summary": {
                details["body_region"]: {
                    "concepts": concepts,
                    "metrics": [metric["metric_name"] for metric in weakest_metrics],
                    "phases": sorted({metric["phase_id"] for metric in weakest_metrics}),
                    "total_weight": round(
                        sum(1 - metric["normalized_score"] for metric in weakest_metrics),
                        4,
                    ),
                    "severity_summary": severity_summary,
                }
            },
            "reasoning_summary": (
                "Synthetic demo ontology: recent coaching signals cluster around "
                f"{focus_category.replace('_', ' ')}."
            ),
            "diagnostic_flags": [DEMO_FLAG],
        },
    )


def _build_choquet_payload(
    *,
    training_session: TrainingSession,
    drill: Drill,
    sport: Sport,
    focus_category: str,
    weakest_metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    details = CATEGORY_DETAILS[focus_category]
    input_values = {
        metric["metric_name"]: round(1 - metric["normalized_score"], 4)
        for metric in weakest_metrics
    }
    choquet_score = round(sum(input_values.values()) / len(input_values), 4)
    group = {
        "concepts": [focus_category, "repeatability"],
        "input_values": input_values,
        "choquet_score": choquet_score,
        "interaction_detected": True,
        "explanation": (
            "Synthetic demo interaction: the same weakness appears across related metrics, "
            "so the dashboard can show a combined coaching pattern."
        ),
    }
    return _model_payload(
        ChoquetAggregationResult,
        {
            "choquet_version": "synthetic_demo_phase4d_v1",
            "status": "COMPLETED",
            "session_id": training_session.id,
            "sport_id": sport.id,
            "drill_id": drill.id,
            "skill_level": training_session.skill_level,
            "concept_aggregation": {focus_category: group},
            "body_region_aggregation": {details["body_region"]: group},
            "overall_choquet_score": choquet_score,
            "dominant_interaction_group": focus_category,
            "diagnostic_flags": [DEMO_FLAG],
        },
    )


def _build_temporal_payload(
    *,
    training_session: TrainingSession,
    drill: Drill,
    sport: Sport,
    focus_category: str,
    overall_score: float,
) -> dict[str, Any]:
    phases = _drill_phases(drill)
    temporal_state = _temporal_state(overall_score, focus_category)
    phase_results = []
    for index, phase in enumerate(phases):
        state = temporal_state if index == len(phases) - 1 else "CONTROLLED"
        phase_results.append(
            {
                "phase_id": phase,
                "frame_count": 42,
                "phase_duration_ms": 1386.0 + (index * 115),
                "valid_frame_ratio": 0.96,
                "average_velocity_proxy": round(_clamp(0.92 - overall_score * 0.25, 0, 1), 4),
                "smoothness_proxy": round(_clamp(overall_score + 0.05, 0, 1), 4),
                "acceleration_change_proxy": round(_clamp(1 - overall_score, 0, 1), 4),
                "temporal_state": state,
                "state_confidence": round(_clamp(0.62 + overall_score * 0.28, 0, 1), 4),
                "diagnostic_flags": [DEMO_FLAG],
            }
        )
    transitions = []
    for left, right in zip(phases, phases[1:]):
        transitions.append(
            {
                "from_phase": left,
                "to_phase": right,
                "transition_valid": True,
                "transition_gap_ms": 33.0,
                "phase_order_valid": True,
                "diagnostic_flags": [DEMO_FLAG],
            }
        )
    return _model_payload(
        TemporalModelingResult,
        {
            "temporal_model_version": "synthetic_demo_phase4f_v1",
            "status": "COMPLETED",
            "session_id": training_session.id,
            "sport_id": sport.id,
            "drill_id": drill.id,
            "skill_level": training_session.skill_level,
            "phase_temporal_results": phase_results,
            "transition_results": transitions,
            "overall_temporal_state": temporal_state,
            "temporal_summary": (
                "Synthetic demo timing summary: tempo control improves across the training history "
                f"with the latest state marked {temporal_state.lower()}."
            ),
            "diagnostic_flags": [DEMO_FLAG],
        },
    )


def _build_llm_payload(
    *,
    training_session: TrainingSession,
    feedback_payload: dict[str, Any],
) -> dict[str, Any]:
    enhanced_items = []
    for item in feedback_payload["prioritized_feedback_items"]:
        enhanced_items.append(
            {
                "phase_id": item["phase_id"],
                "metric_id": item["metric_id"],
                "metric_name": item["metric_name"],
                "severity_level": item["severity_level"],
                "priority_rank": item["priority_rank"],
                "affected_body_part": item["affected_body_part"],
                "issue_direction": item["issue_direction"],
                "deterministic_coaching_cue": item["coaching_cue"],
                "llm_coaching_cue": item["coaching_cue"],
                "deterministic_improvement_suggestion": item["improvement_suggestion"],
                "llm_improvement_suggestion": item["improvement_suggestion"],
                "grounding_fields_used": ["metric_name", "phase_id", "coaching_cue"],
                "fallback_used": True,
            }
        )
    return _model_payload(
        LLMFeedbackResult,
        {
            "llm_feedback_version": "synthetic_demo_phase3b_v1",
            "status": "COMPLETED",
            "session_id": training_session.id,
            "provider": "synthetic_demo",
            "model": "deterministic-demo-fallback-v1",
            "fallback_used": True,
            "advanced_context_used": True,
            "advanced_context_sources": [
                "synthetic_demo_evaluation",
                "synthetic_demo_pedagogy",
                "synthetic_demo_temporal",
            ],
            "context_diagnostic_flags": [DEMO_FLAG],
            "enhanced_feedback_items": enhanced_items,
            "enhanced_summary": {
                "deterministic_summary": feedback_payload["overall_feedback_summary"],
                "llm_summary": (
                    "Synthetic demo fallback summary: coaching text is generated from seeded "
                    "deterministic feedback, not an external model or real study."
                ),
                "grounding_fields_used": ["overall_feedback_summary", "prioritized_feedback_items"],
                "fallback_used": True,
            },
            "diagnostic_flags": [DEMO_FLAG, "LLM_FALLBACK_SYNTHETIC_DEMO"],
        },
    )


def _create_session_summary(
    *,
    session: TrainingSession,
    drill: Drill,
    sport: Sport,
    overall_score: float,
    strongest_metrics: list[dict[str, Any]],
    feedback_items: list[dict[str, Any]],
    created_at: datetime,
) -> SessionSummary:
    weaknesses = [
        {
            "metric": item["metric_name"],
            "severity": item["severity_level"],
            "issue_label": item["issue_title"],
        }
        for item in feedback_items
    ]
    summary = SessionSummary(
        session_id=session.id,
        summary_text=(
            f"Synthetic demo session for {sport.sport_name} · {drill.drill_name}: "
            f"overall score {round(overall_score * 100)} with coaching focus on "
            f"{feedback_items[0]['metric_name'].replace('_', ' ')}."
        ),
        overall_accuracy=_decimal(overall_score * 100, places=2),
        strengths={
            "metrics": [
                {"name": item["metric_name"], "score": item["score"]}
                for item in strongest_metrics[:2]
            ]
        },
        weaknesses={"issues": weaknesses},
        recommendations={
            "actions": [item["improvement_suggestion"] for item in feedback_items]
        },
        created_at=created_at,
    )
    return summary


def _create_demo_session(
    *,
    db,
    user: User,
    drill: Drill,
    sport: Sport,
    metric_types_by_name: dict[str, MetricType],
    session_index: int,
    start_time: datetime,
    rng: random.Random,
) -> DemoCounts:
    focus_sequence = DRILL_FOCUS_SEQUENCE.get(drill.drill_name, ["posture"])
    focus_category = focus_sequence[(session_index // len(focus_sequence)) % len(focus_sequence)]
    target_score = _target_score_for_session(session_index, drill.drill_name, rng)
    metric_payloads = _build_metric_payloads(
        drill=drill,
        metric_types_by_name=metric_types_by_name,
        session_index=session_index,
        target_score=target_score,
        focus_category=focus_category,
        rng=rng,
    )
    actual_overall_score = round(
        sum(metric["normalized_score"] for metric in metric_payloads) / len(metric_payloads),
        4,
    )
    input_type = InputType.LIVE if session_index % 5 == 2 else InputType.UPLOAD
    end_time = start_time + timedelta(minutes=8 + (session_index % 7))
    training_session = TrainingSession(
        user_id=user.id,
        drill_id=drill.id,
        input_type=input_type,
        skill_level=SkillLevel.INTERMEDIATE,
        camera_view=_camera_view_for_drill(drill),
        dominant_side=DominantSide.RIGHT
        if sport.sport_name in {"Football", "Basketball"}
        else None,
        status=SessionStatus.COMPLETED,
        start_time=start_time,
        end_time=end_time,
        created_at=start_time,
    )
    db.add(training_session)
    db.flush()

    evaluation_payload = _build_evaluation_payload(
        training_session=training_session,
        drill=drill,
        sport=sport,
        metric_payloads=metric_payloads,
    )
    sorted_metrics = sorted(metric_payloads, key=lambda item: item["normalized_score"])
    weakest_metrics = sorted_metrics[:3]
    feedback_payload, feedback_items = _build_feedback_payload(
        training_session=training_session,
        weakest_metrics=weakest_metrics,
    )
    fuzzy_payload = _build_fuzzy_payload(
        training_session=training_session,
        drill=drill,
        sport=sport,
        metric_payloads=metric_payloads,
    )
    it2_payload = _build_it2_payload(
        training_session=training_session,
        drill=drill,
        sport=sport,
        metric_payloads=metric_payloads,
    )
    pedagogy_payload = _build_pedagogy_payload(
        training_session=training_session,
        drill=drill,
        sport=sport,
        feedback_items=feedback_items,
    )
    ontology_payload = _build_ontology_payload(
        training_session=training_session,
        drill=drill,
        sport=sport,
        focus_category=focus_category,
        weakest_metrics=weakest_metrics,
    )
    choquet_payload = _build_choquet_payload(
        training_session=training_session,
        drill=drill,
        sport=sport,
        focus_category=focus_category,
        weakest_metrics=weakest_metrics,
    )
    temporal_payload = _build_temporal_payload(
        training_session=training_session,
        drill=drill,
        sport=sport,
        focus_category=focus_category,
        overall_score=actual_overall_score,
    )
    llm_payload = _build_llm_payload(
        training_session=training_session,
        feedback_payload=feedback_payload,
    )

    artifact_payloads = {
        "evaluation_result": evaluation_payload,
        "feedback_result": feedback_payload,
        "fuzzy_interpretation_result": fuzzy_payload,
        "it2_fuzzy_interpretation_result": it2_payload,
        "pedagogical_decision_result": pedagogy_payload,
        "ontology_reasoning_result": ontology_payload,
        "choquet_aggregation_result": choquet_payload,
        "temporal_modeling_result": temporal_payload,
        "llm_feedback_result": llm_payload,
    }
    for artifact_type, payload in artifact_payloads.items():
        db.add(
            SessionArtifact(
                session_id=training_session.id,
                artifact_type=artifact_type,
                payload_json=payload,
                created_at=end_time,
            )
        )

    strongest_metrics = sorted(
        evaluation_payload["strongest_metrics"],
        key=lambda item: item["score"],
        reverse=True,
    )
    summary = _create_session_summary(
        session=training_session,
        drill=drill,
        sport=sport,
        overall_score=actual_overall_score,
        strongest_metrics=strongest_metrics,
        feedback_items=feedback_items,
        created_at=end_time,
    )
    db.add(summary)
    db.flush()

    for metric in metric_payloads:
        db.add(
            MetricResult(
                session_id=training_session.id,
                metric_id=metric["metric_type_id"],
                phase_id=metric["phase_id"],
                raw_value=_decimal(metric["raw_value"]),
                unit=metric["unit"],
                ideal_min=_decimal(metric["ideal_min"]),
                ideal_max=_decimal(metric["ideal_max"]),
                deviation=_decimal(metric["deviation"]),
                severity_level=SeverityLevel(metric["severity_level"]),
                normalized_score=_decimal(metric["normalized_score"]),
                affected_body_part=metric["affected_body_part"],
                computation_status=ComputationStatus.COMPUTED,
                valid_frame_count=metric["valid_frame_count"],
                formula_version=metric["formula_version"],
                created_at=end_time,
            )
        )
        db.add(
            ProgressRecord(
                user_id=user.id,
                summary_id=summary.id,
                metric_id=metric["metric_type_id"],
                metric_value=_decimal(metric["normalized_score"]),
                date_recorded=start_time.date(),
                created_at=end_time,
            )
        )

    for item in feedback_items:
        db.add(
            Feedback(
                session_id=training_session.id,
                severity_level=SeverityLevel(item["severity_level"]),
                technique_issue=f"Synthetic demo: {item['issue_title']}",
                coaching_cue=item["coaching_cue"],
                metric_snapshot={
                    "synthetic_demo": True,
                    "metric_name": item["metric_name"],
                    "phase_id": item["phase_id"],
                    "priority_rank": item["priority_rank"],
                },
                created_at=end_time,
            )
        )

    return DemoCounts(
        sessions=1,
        summaries=1,
        progress_records=len(metric_payloads),
        metric_results=len(metric_payloads),
        artifacts=len(artifact_payloads),
        feedback_rows=len(feedback_items),
    )


def _combine_counts(left: DemoCounts, right: DemoCounts) -> DemoCounts:
    return DemoCounts(
        sessions=left.sessions + right.sessions,
        summaries=left.summaries + right.summaries,
        progress_records=left.progress_records + right.progress_records,
        metric_results=left.metric_results + right.metric_results,
        artifacts=left.artifacts + right.artifacts,
        feedback_rows=left.feedback_rows + right.feedback_rows,
    )


def _load_seeded_references(db) -> tuple[dict[str, Sport], list[tuple[Sport, Drill]], dict[str, MetricType]]:
    sports_by_name = {
        sport.sport_name: sport
        for sport in db.scalars(select(Sport).order_by(Sport.sport_name)).all()
    }
    drills = (
        db.scalars(
            select(Drill)
            .options(selectinload(Drill.sport))
            .order_by(Drill.drill_name)
        )
        .unique()
        .all()
    )
    drill_order = [
        ("Gym", "Bodyweight Squat"),
        ("Gym", "Dumbbell Shoulder Press"),
        ("Basketball", "Set Shot Form"),
        ("Basketball", "Defensive Stance"),
        ("Football", "Instep Pass"),
        ("Football", "Basic Shooting Form"),
    ]
    drills_by_key = {(drill.sport.sport_name, drill.drill_name): drill for drill in drills}
    selected_drills: list[tuple[Sport, Drill]] = []
    for sport_name, drill_name in drill_order:
        sport = sports_by_name.get(sport_name)
        drill = drills_by_key.get((sport_name, drill_name))
        if sport is None or drill is None:
            raise RuntimeError(f"Missing seeded drill: {sport_name} / {drill_name}")
        selected_drills.append((sport, drill))

    metric_types_by_name = {
        metric.metric_name: metric
        for metric in db.scalars(select(MetricType).order_by(MetricType.metric_name)).all()
    }
    missing_metrics = sorted(
        {
            metric_name
            for _, drill in selected_drills
            for metric_name in _drill_metric_names(drill)
            if metric_name not in metric_types_by_name
        }
    )
    if missing_metrics:
        raise RuntimeError(f"Missing seeded metric types: {', '.join(missing_metrics)}")
    return sports_by_name, selected_drills, metric_types_by_name


def seed_demo_athlete() -> DemoCounts:
    rng = random.Random(RNG_SEED)
    total_counts = DemoCounts()
    anchor = datetime.now(UTC).replace(hour=17, minute=30, second=0, microsecond=0)

    with SessionLocal() as db:
        try:
            sports_by_name, _ = seed_sports(db)
            metric_types_by_name, _ = seed_metric_types(db)
            seed_drills(db, sports_by_name, set(metric_types_by_name.keys()))
            db.flush()

            existing_demo = db.scalar(select(User).where(User.email == DEMO_EMAIL))
            if existing_demo is not None:
                db.delete(existing_demo)
                db.flush()

            sports_by_name, selected_drills, metric_types_by_name = _load_seeded_references(db)
            gym = sports_by_name["Gym"]
            user = User(
                full_name=DEMO_NAME,
                email=DEMO_EMAIL,
                password_hash=hash_password(DEMO_PASSWORD),
                created_at=anchor - timedelta(days=95),
            )
            db.add(user)
            db.flush()
            db.add(
                UserProfile(
                    user_id=user.id,
                    sport_id=gym.id,
                    height_cm=Decimal("176.00"),
                    weight_kg=Decimal("72.50"),
                    skill_level=SkillLevel.INTERMEDIATE,
                    injury_notes=(
                        "Synthetic demo profile: multi-sport trainee history for supervisor "
                        "dashboard demonstrations only. Not real athlete or validation data."
                    ),
                    created_at=anchor - timedelta(days=95),
                )
            )

            for index in range(DEMO_SESSION_COUNT):
                sport, drill = selected_drills[index % len(selected_drills)]
                days_ago = round(88 - ((index / (DEMO_SESSION_COUNT - 1)) * 88))
                start_time = anchor - timedelta(
                    days=days_ago,
                    hours=(index % 4),
                    minutes=(index % 3) * 7,
                )
                counts = _create_demo_session(
                    db=db,
                    user=user,
                    drill=drill,
                    sport=sport,
                    metric_types_by_name=metric_types_by_name,
                    session_index=index,
                    start_time=start_time,
                    rng=rng,
                )
                total_counts = _combine_counts(total_counts, counts)

            db.commit()
            return total_counts
        except Exception:
            db.rollback()
            raise


def main() -> None:
    counts = seed_demo_athlete()
    print("Synthetic TrainUp demo athlete seeded.")
    print("This data is synthetic/demo only and is not validation or user-study data.")
    print(f"Demo login: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    print(f"sessions: {counts.sessions}")
    print(f"session summaries: {counts.summaries}")
    print(f"progress records: {counts.progress_records}")
    print(f"metric results: {counts.metric_results}")
    print(f"session artifacts: {counts.artifacts}")
    print(f"feedback rows: {counts.feedback_rows}")
    print("Run again any time to reset and recreate only this demo athlete dataset.")


if __name__ == "__main__":
    main()
