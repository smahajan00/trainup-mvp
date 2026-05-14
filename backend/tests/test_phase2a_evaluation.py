from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select

from app.engines.cognition_engine.phase2a_contract import (
    BASIC_SHOOTING_FORM_CONTRACT,
    BODYWEIGHT_SQUAT_CONTRACT,
    DEFENSIVE_STANCE_CONTRACT,
    DUMBBELL_SHOULDER_PRESS_CONTRACT,
    INSTEP_PASS_CONTRACT,
    SET_SHOT_FORM_CONTRACT,
    MetricContract,
)
from app.engines.cognition_engine.phase2a_evaluator import (
    METRIC_CALCULATOR_REGISTRY,
    SEGMENTATION_REGISTRY,
    PhaseSegmentationError,
    Phase2AEvaluator,
)
from app.models.drill import Drill
from app.models.enums import CameraView, ComputationStatus, DominantSide, SeverityLevel
from app.models.feedback import Feedback
from app.models.metric_result import MetricResult
from app.models.session_artifact import SessionArtifact
from app.schemas.session import PoseFrameResponse, PoseLandmarkCoordinate, PoseSequenceResponse
from app.services.dominant_side_detector import DominantSideDetector
from app.services.session_service import (
    SAGITTAL_LANDMARK_SWAP_PAIRS,
    normalize_pose_sequence_for_camera_view,
)

SUPPORTED_CONTRACTS = (
    BODYWEIGHT_SQUAT_CONTRACT,
    SET_SHOT_FORM_CONTRACT,
    DUMBBELL_SHOULDER_PRESS_CONTRACT,
    DEFENSIVE_STANCE_CONTRACT,
    INSTEP_PASS_CONTRACT,
    BASIC_SHOOTING_FORM_CONTRACT,
)
EXPECTED_EVALUATION_VERSION = "phase2c_v0_1_0"


def _register_user(client, *, email: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Phase 2A Evaluator",
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
    *,
    drill: Drill,
    skill_level: str,
    camera_view: str | None = None,
    dominant_side: str | None = None,
) -> dict[str, str]:
    payload = {
        "sport_id": str(drill.sport_id),
        "skill_level": skill_level,
        "drill_id": str(drill.id),
        "input_type": "UPLOAD",
    }
    if camera_view is not None:
        payload["camera_view"] = camera_view
    if dominant_side is not None:
        payload["dominant_side"] = dominant_side

    response = client.post(
        "/api/sessions",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


def _landmark(x: float, y: float, visibility: float = 0.96) -> PoseLandmarkCoordinate:
    return PoseLandmarkCoordinate(x=round(x, 6), y=round(y, 6), visibility=visibility)


def _pose_frame(
    session_id: str,
    *,
    frame_index: int,
    landmarks: dict[str, PoseLandmarkCoordinate],
    timestamp_ms: float | None = None,
) -> PoseFrameResponse:
    return PoseFrameResponse(
        session_id=UUID(session_id),
        frame_index=frame_index,
        timestamp_ms=timestamp_ms if timestamp_ms is not None else frame_index * 33.333,
        landmarks=landmarks,
        frame_valid=True,
        diagnostic_flags=[],
    )


def _pose_sequence(session_id: str, frames: list[PoseFrameResponse]) -> PoseSequenceResponse:
    return PoseSequenceResponse(
        session_id=UUID(session_id),
        pose_model="mediapipe_pose",
        preprocessing_version="phase1_v0_1_0",
        frame_count=len(frames),
        valid_frame_count=sum(1 for frame in frames if frame.frame_valid),
        status="COMPLETED",
        diagnostic_flags=[],
        sequence_data=frames,
        created_at=None,
    )


def _store_pose_sequence(db_session, *, session_id: str, frames: list[PoseFrameResponse]) -> None:
    pose_sequence = _pose_sequence(session_id, frames)
    db_session.add(
        SessionArtifact(
            session_id=UUID(session_id),
            artifact_type="pose_sequence",
            payload_json=pose_sequence.model_dump(mode="json", exclude={"created_at"}),
        )
    )
    db_session.commit()


def _swap_sagittal_landmarks(frames: list[PoseFrameResponse]) -> list[PoseFrameResponse]:
    swapped_frames = []
    for frame in frames:
        landmarks = dict(frame.landmarks)
        for left_name, right_name in SAGITTAL_LANDMARK_SWAP_PAIRS:
            left_landmark = landmarks.get(left_name)
            right_landmark = landmarks.get(right_name)
            if right_landmark is not None:
                landmarks[left_name] = right_landmark
            if left_landmark is not None:
                landmarks[right_name] = left_landmark
        swapped_frames.append(frame.model_copy(update={"landmarks": landmarks}))

    return swapped_frames


def _assert_stable_evaluation_artifact_shape(
    payload: dict,
    *,
    expected_phases: list[str],
) -> None:
    expected_top_level_keys = {
        "evaluation_version",
        "status",
        "session_id",
        "sport_id",
        "skill_level",
        "drill_id",
        "phase_results",
        "overall_score",
        "overall_severity",
        "detected_issues",
        "strongest_metrics",
        "weakest_metrics",
        "diagnostic_flags",
    }
    optional_top_level_keys = {
        "requested_dominant_side",
        "resolved_dominant_side",
        "dominant_side_confidence",
        "dominant_side_diagnostic_flags",
        "detected_rep_count",
        "evaluated_rep_count",
        "rep_summaries",
        "set_level_summary",
    }
    assert expected_top_level_keys <= set(payload)
    assert set(payload) <= expected_top_level_keys | optional_top_level_keys
    assert payload["evaluation_version"] == EXPECTED_EVALUATION_VERSION
    assert [phase["phase_id"] for phase in payload["phase_results"]] == expected_phases
    assert payload["strongest_metrics"]
    assert payload["weakest_metrics"]
    assert set(payload["strongest_metrics"][0]) == {
        "phase_id",
        "metric_id",
        "metric_name",
        "score",
    }
    assert all(
        phase["frame_range"]["boundary_mode"] == "inclusive_overlapping"
        for phase in payload["phase_results"]
    )
    assert all(
        set(phase) == {
            "phase_id",
            "frame_range",
            "metric_results",
            "phase_score",
            "phase_severity",
            "detected_issues",
        }
        for phase in payload["phase_results"]
    )
    assert all(
        set(phase["frame_range"]) == {
            "phase_id",
            "start_frame_index",
            "end_frame_index",
            "start_timestamp_ms",
            "end_timestamp_ms",
            "boundary_mode",
        }
        for phase in payload["phase_results"]
    )
    metric_keys = {
        "metric_id",
        "metric_name",
        "phase_id",
        "raw_value",
        "unit",
        "ideal_min",
        "ideal_max",
        "deviation",
        "issue_direction",
        "severity_level",
        "normalized_score",
        "affected_body_part",
        "computation_status",
        "valid_frame_count",
        "formula_version",
        "diagnostic_flags",
    }
    assert all(
        set(metric) == metric_keys
        for phase in payload["phase_results"]
        for metric in phase["metric_results"]
    )
    issue_keys = {
        "phase_id",
        "metric_id",
        "metric_name",
        "severity_level",
        "affected_body_part",
        "deviation",
        "issue_direction",
        "computation_status",
        "diagnostic_flags",
    }
    assert all(set(issue) == issue_keys for issue in payload["detected_issues"])
    assert all(
        set(issue) == issue_keys
        for phase in payload["phase_results"]
        for issue in phase["detected_issues"]
    )
    assert all(
        {"phase_id", "metric_id", "metric_name", "score"} <= set(metric)
        for metric in payload["strongest_metrics"] + payload["weakest_metrics"]
    )
    assert all(
        set(metric) == {"phase_id", "metric_id", "metric_name", "score"}
        for metric in payload["strongest_metrics"] + payload["weakest_metrics"]
    )


def _squat_pose_frames(session_id: str, frame_count: int = 36) -> list[PoseFrameResponse]:
    frames: list[PoseFrameResponse] = []
    for frame_index in range(frame_count):
        if frame_index < 9:
            bend = 0.0
        elif frame_index <= 22:
            bend = (frame_index - 8) / 14
        else:
            bend = max((frame_count - 1 - frame_index) / 13, 0.0)

        hip_y = 0.47 + (bend * 0.12)
        knee_y = 0.67 + (bend * 0.03)
        shoulder_y = hip_y - 0.30
        left_hip_x = 0.42
        right_hip_x = 0.58
        left_knee_x = 0.40 + (bend * 0.07)
        right_knee_x = 0.60 - (bend * 0.07)

        landmarks = {
            "nose": _landmark(0.50, shoulder_y - 0.12),
            "left_shoulder": _landmark(0.43, shoulder_y),
            "right_shoulder": _landmark(0.57, shoulder_y),
            "left_elbow": _landmark(0.40, shoulder_y + 0.12),
            "right_elbow": _landmark(0.60, shoulder_y + 0.12),
            "left_wrist": _landmark(0.39, shoulder_y + 0.24),
            "right_wrist": _landmark(0.61, shoulder_y + 0.24),
            "left_hip": _landmark(left_hip_x, hip_y),
            "right_hip": _landmark(right_hip_x, hip_y),
            "left_knee": _landmark(left_knee_x, knee_y),
            "right_knee": _landmark(right_knee_x, knee_y),
            "left_ankle": _landmark(0.39, 0.86),
            "right_ankle": _landmark(0.61, 0.86),
            "left_heel": _landmark(0.37, 0.88),
            "right_heel": _landmark(0.63, 0.88),
            "left_foot_index": _landmark(0.41, 0.90),
            "right_foot_index": _landmark(0.59, 0.90),
        }
        frames.append(
            PoseFrameResponse(
                session_id=UUID(session_id),
                frame_index=frame_index,
                timestamp_ms=frame_index * 33.333,
                landmarks=landmarks,
                frame_valid=True,
                diagnostic_flags=[],
            )
        )
    return frames


def _squat_depth_landmarks(
    *,
    left_hip_x: float,
    left_ankle_x: float,
) -> dict[str, PoseLandmarkCoordinate]:
    right_hip_x = 1.0 - left_hip_x
    right_ankle_x = 1.0 - left_ankle_x
    return {
        "left_shoulder": _landmark(0.43, 0.25),
        "right_shoulder": _landmark(0.57, 0.25),
        "left_hip": _landmark(left_hip_x, 0.55),
        "right_hip": _landmark(right_hip_x, 0.55),
        "left_knee": _landmark(0.50, 0.70),
        "right_knee": _landmark(0.50, 0.70),
        "left_ankle": _landmark(left_ankle_x, 0.85),
        "right_ankle": _landmark(right_ankle_x, 0.85),
    }


def _squat_depth_cycle_frames(
    session_id: str,
    *,
    start_frame_index: int,
    bottom: str = "good",
) -> list[PoseFrameResponse]:
    bottom_points = {
        "good": (0.35, 0.45),
        "shallow": (0.42, 0.49),
    }
    bottom_hip_x, bottom_ankle_x = bottom_points[bottom]
    high_hip_x = 0.45
    high_ankle_x = 0.50
    progress_values = [0.0, 0.35, 0.7, 1.0, 0.7, 0.35, 0.0]
    frames: list[PoseFrameResponse] = []
    for offset, progress in enumerate(progress_values):
        left_hip_x = high_hip_x + ((bottom_hip_x - high_hip_x) * progress)
        left_ankle_x = high_ankle_x + ((bottom_ankle_x - high_ankle_x) * progress)
        frame_index = start_frame_index + offset
        frames.append(
            _pose_frame(
                session_id,
                frame_index=frame_index,
                timestamp_ms=frame_index * 33.333,
                landmarks=_squat_depth_landmarks(
                    left_hip_x=left_hip_x,
                    left_ankle_x=left_ankle_x,
                ),
            )
        )
    return frames


def _offset_frames(
    frames: list[PoseFrameResponse],
    *,
    start_frame_index: int,
) -> list[PoseFrameResponse]:
    return [
        frame.model_copy(
            update={
                "frame_index": start_frame_index + offset,
                "timestamp_ms": (start_frame_index + offset) * 33.333,
            }
        )
        for offset, frame in enumerate(frames)
    ]


def _multi_rep_squat_depth_frames(
    session_id: str,
    *,
    pattern: list[str],
) -> list[PoseFrameResponse]:
    frames: list[PoseFrameResponse] = []
    next_frame_index = 0
    for bottom in pattern:
        cycle = _squat_depth_cycle_frames(
            session_id,
            start_frame_index=next_frame_index,
            bottom=bottom,
        )
        frames.extend(cycle if not frames else cycle[1:])
        next_frame_index = frames[-1].frame_index + 1
    return frames


def _multi_rep_shoulder_press_frames(
    session_id: str,
    *,
    rep_count: int = 2,
) -> list[PoseFrameResponse]:
    frames: list[PoseFrameResponse] = []
    next_frame_index = 0
    for _ in range(rep_count):
        cycle = _offset_frames(
            _shoulder_press_pose_frames(session_id),
            start_frame_index=next_frame_index,
        )
        frames.extend(cycle if not frames else cycle[1:])
        next_frame_index = frames[-1].frame_index + 1
    return frames


def _multi_cycle_defensive_stance_frames(
    session_id: str,
    *,
    cycle_count: int = 2,
) -> list[PoseFrameResponse]:
    frames: list[PoseFrameResponse] = []
    next_frame_index = 0
    for _ in range(cycle_count):
        cycle = _offset_frames(
            _defensive_stance_pose_frames(session_id),
            start_frame_index=next_frame_index,
        )
        frames.extend(cycle if not frames else cycle[1:])
        next_frame_index = frames[-1].frame_index + 1
    return frames


def _defensive_stance_low_motion_frames(session_id: str) -> list[PoseFrameResponse]:
    frames: list[PoseFrameResponse] = []
    knee_x_by_frame = [0.498, 0.498, 0.498, 0.498, 0.502, 0.502, 0.502, 0.502, 0.499, 0.499]
    for frame_index, left_knee_x in enumerate(knee_x_by_frame):
        right_knee_x = 1.0 - left_knee_x
        hip_y = 0.60
        shoulder_y = 0.32
        landmarks = {
            "nose": _landmark(0.50, 0.20),
            "left_shoulder": _landmark(0.41, shoulder_y),
            "right_shoulder": _landmark(0.59, shoulder_y),
            "left_elbow": _landmark(0.37, shoulder_y + 0.13),
            "right_elbow": _landmark(0.63, shoulder_y + 0.13),
            "left_wrist": _landmark(0.36, shoulder_y + 0.23),
            "right_wrist": _landmark(0.64, shoulder_y + 0.23),
            "left_hip": _landmark(0.45, hip_y),
            "right_hip": _landmark(0.55, hip_y),
            "left_knee": _landmark(left_knee_x, 0.74),
            "right_knee": _landmark(right_knee_x, 0.74),
            "left_ankle": _landmark(0.38, 0.91),
            "right_ankle": _landmark(0.62, 0.91),
            "left_heel": _landmark(0.37, 0.93),
            "right_heel": _landmark(0.63, 0.93),
            "left_foot_index": _landmark(0.40, 0.95),
            "right_foot_index": _landmark(0.60, 0.95),
        }
        frames.append(
            PoseFrameResponse(
                session_id=UUID(session_id),
                frame_index=frame_index,
                timestamp_ms=frame_index * 33.333,
                landmarks=landmarks,
                frame_valid=True,
                diagnostic_flags=[],
            )
        )
    return frames


def _set_shot_pose_frames(
    session_id: str,
    frame_count: int = 40,
    dominant_side: str = "RIGHT",
) -> list[PoseFrameResponse]:
    frames: list[PoseFrameResponse] = []
    for frame_index in range(frame_count):
        if frame_index < 12:
            wrist_y = 0.56
            elbow_y = 0.46
            wrist_x = 0.60
        elif frame_index < 22:
            wrist_y = 0.64 - ((frame_index - 12) * 0.018)
            elbow_y = 0.48 - ((frame_index - 12) * 0.010)
            wrist_x = 0.62 - ((frame_index - 12) * 0.005)
        elif frame_index < 30:
            wrist_y = 0.42 - ((frame_index - 22) * 0.030)
            elbow_y = 0.36 - ((frame_index - 22) * 0.015)
            wrist_x = 0.57
        else:
            wrist_y = 0.18
            elbow_y = 0.28
            wrist_x = 0.56

        moving_wrist_x = wrist_x
        moving_wrist_y = wrist_y
        moving_elbow_y = elbow_y
        static_wrist_x = 0.41 if dominant_side == "RIGHT" else 0.62
        static_wrist_y = 0.60
        static_elbow_y = 0.48

        landmarks = {
            "nose": _landmark(0.50, 0.22),
            "left_shoulder": _landmark(0.44, 0.36),
            "right_shoulder": _landmark(0.56, 0.36),
            "left_elbow": _landmark(0.42, moving_elbow_y if dominant_side == "LEFT" else static_elbow_y),
            "right_elbow": _landmark(0.56, moving_elbow_y if dominant_side == "RIGHT" else static_elbow_y),
            "left_wrist": _landmark(moving_wrist_x if dominant_side == "LEFT" else static_wrist_x, moving_wrist_y if dominant_side == "LEFT" else static_wrist_y),
            "right_wrist": _landmark(moving_wrist_x if dominant_side == "RIGHT" else static_wrist_x, moving_wrist_y if dominant_side == "RIGHT" else static_wrist_y),
            "left_hip": _landmark(0.45, 0.58),
            "right_hip": _landmark(0.55, 0.58),
            "left_knee": _landmark(0.44, 0.73),
            "right_knee": _landmark(0.56, 0.73),
            "left_ankle": _landmark(0.43, 0.90),
            "right_ankle": _landmark(0.57, 0.90),
            "left_heel": _landmark(0.42, 0.92),
            "right_heel": _landmark(0.58, 0.92),
            "left_foot_index": _landmark(0.45, 0.94),
            "right_foot_index": _landmark(0.55, 0.94),
        }
        frames.append(
            PoseFrameResponse(
                session_id=UUID(session_id),
                frame_index=frame_index,
                timestamp_ms=frame_index * 33.333,
                landmarks=landmarks,
                frame_valid=True,
                diagnostic_flags=[],
            )
        )
    return frames


def _shoulder_press_pose_frames(session_id: str, frame_count: int = 44) -> list[PoseFrameResponse]:
    frames: list[PoseFrameResponse] = []
    for frame_index in range(frame_count):
        if frame_index < 10:
            progress = 0.0
        elif frame_index < 24:
            progress = (frame_index - 9) / 15
        elif frame_index < 32:
            progress = 1.0
        else:
            progress = max((frame_count - 1 - frame_index) / 11, 0.0)

        shoulder_y = 0.34
        hip_y = 0.62
        elbow_y = 0.44 - (progress * 0.20)
        wrist_y = 0.48 - (progress * 0.32)
        left_elbow_x = 0.42
        right_elbow_x = 0.58
        left_wrist_x = left_elbow_x + (0.01 * (1 - progress))
        right_wrist_x = right_elbow_x - (0.01 * (1 - progress))

        landmarks = {
            "nose": _landmark(0.50, 0.20),
            "left_shoulder": _landmark(0.43, shoulder_y),
            "right_shoulder": _landmark(0.57, shoulder_y),
            "left_elbow": _landmark(left_elbow_x, elbow_y),
            "right_elbow": _landmark(right_elbow_x, elbow_y),
            "left_wrist": _landmark(left_wrist_x, wrist_y),
            "right_wrist": _landmark(right_wrist_x, wrist_y),
            "left_hip": _landmark(0.45, hip_y),
            "right_hip": _landmark(0.55, hip_y),
            "left_knee": _landmark(0.45, 0.78),
            "right_knee": _landmark(0.55, 0.78),
            "left_ankle": _landmark(0.44, 0.93),
            "right_ankle": _landmark(0.56, 0.93),
            "left_heel": _landmark(0.43, 0.95),
            "right_heel": _landmark(0.57, 0.95),
            "left_foot_index": _landmark(0.46, 0.97),
            "right_foot_index": _landmark(0.54, 0.97),
        }
        frames.append(
            PoseFrameResponse(
                session_id=UUID(session_id),
                frame_index=frame_index,
                timestamp_ms=frame_index * 33.333,
                landmarks=landmarks,
                frame_valid=True,
                diagnostic_flags=[],
            )
        )
    return frames


def _defensive_stance_pose_frames(session_id: str, frame_count: int = 38) -> list[PoseFrameResponse]:
    frames: list[PoseFrameResponse] = []
    for frame_index in range(frame_count):
        if frame_index < 8:
            bend = 0.0
        elif frame_index < 16:
            bend = (frame_index - 7) / 9
        elif frame_index < 28:
            bend = 1.0
        else:
            bend = max((frame_count - 1 - frame_index) / 9, 0.0)

        hip_y = 0.55 + (bend * 0.08)
        knee_y = 0.72 + (bend * 0.02)
        shoulder_y = hip_y - 0.28
        left_knee_x = 0.43 + (bend * 0.10)
        right_knee_x = 0.57 - (bend * 0.10)

        landmarks = {
            "nose": _landmark(0.50, shoulder_y - 0.12),
            "left_shoulder": _landmark(0.41, shoulder_y),
            "right_shoulder": _landmark(0.59, shoulder_y),
            "left_elbow": _landmark(0.37, shoulder_y + 0.13),
            "right_elbow": _landmark(0.63, shoulder_y + 0.13),
            "left_wrist": _landmark(0.36, shoulder_y + 0.23),
            "right_wrist": _landmark(0.64, shoulder_y + 0.23),
            "left_hip": _landmark(0.45, hip_y),
            "right_hip": _landmark(0.55, hip_y),
            "left_knee": _landmark(left_knee_x, knee_y),
            "right_knee": _landmark(right_knee_x, knee_y),
            "left_ankle": _landmark(0.38, 0.91),
            "right_ankle": _landmark(0.62, 0.91),
            "left_heel": _landmark(0.37, 0.93),
            "right_heel": _landmark(0.63, 0.93),
            "left_foot_index": _landmark(0.40, 0.95),
            "right_foot_index": _landmark(0.60, 0.95),
        }
        frames.append(
            PoseFrameResponse(
                session_id=UUID(session_id),
                frame_index=frame_index,
                timestamp_ms=frame_index * 33.333,
                landmarks=landmarks,
                frame_valid=True,
                diagnostic_flags=[],
            )
        )
    return frames


def _instep_pass_pose_frames(
    session_id: str,
    frame_count: int = 42,
    dominant_side: str = "RIGHT",
) -> list[PoseFrameResponse]:
    frames: list[PoseFrameResponse] = []
    for frame_index in range(frame_count):
        if frame_index < 10:
            progress = 0.0
        elif frame_index < 20:
            progress = (frame_index - 9) / 11
        elif frame_index < 28:
            progress = 1.0 - ((frame_index - 20) / 8)
        else:
            progress = -((frame_index - 27) / 14)

        if progress >= 0:
            moving_knee_x = 0.58 + (0.04 * progress)
            moving_knee_y = 0.72
            moving_ankle_x = 0.64 + (0.09 * progress)
            moving_ankle_y = 0.90 - (0.10 * progress)
        else:
            through = min(abs(progress), 1.0)
            moving_knee_x = 0.56 - (0.03 * through)
            moving_knee_y = 0.72
            moving_ankle_x = 0.47 - (0.12 * through)
            moving_ankle_y = 0.90 - (0.08 * through)

        static_knee_x = 0.43 if dominant_side == "RIGHT" else 0.57
        static_knee_y = 0.73
        static_ankle_x = 0.43 if dominant_side == "RIGHT" else 0.57
        static_ankle_y = 0.90

        landmarks = {
            "nose": _landmark(0.50, 0.22),
            "left_shoulder": _landmark(0.42, 0.34),
            "right_shoulder": _landmark(0.58, 0.34),
            "left_elbow": _landmark(0.39, 0.48),
            "right_elbow": _landmark(0.61, 0.48),
            "left_wrist": _landmark(0.38, 0.60),
            "right_wrist": _landmark(0.62, 0.60),
            "left_hip": _landmark(0.45, 0.56),
            "right_hip": _landmark(0.55, 0.56),
            "left_knee": _landmark(
                moving_knee_x if dominant_side == "LEFT" else static_knee_x,
                moving_knee_y if dominant_side == "LEFT" else static_knee_y,
            ),
            "right_knee": _landmark(
                moving_knee_x if dominant_side == "RIGHT" else static_knee_x,
                moving_knee_y if dominant_side == "RIGHT" else static_knee_y,
            ),
            "left_ankle": _landmark(
                moving_ankle_x if dominant_side == "LEFT" else static_ankle_x,
                moving_ankle_y if dominant_side == "LEFT" else static_ankle_y,
            ),
            "right_ankle": _landmark(
                moving_ankle_x if dominant_side == "RIGHT" else static_ankle_x,
                moving_ankle_y if dominant_side == "RIGHT" else static_ankle_y,
            ),
            "left_heel": _landmark(0.41, 0.92),
            "right_heel": _landmark(
                (moving_ankle_x if dominant_side == "RIGHT" else static_ankle_x) + 0.02,
                (moving_ankle_y if dominant_side == "RIGHT" else static_ankle_y) + 0.02,
            ),
            "left_foot_index": _landmark(0.45, 0.94),
            "right_foot_index": _landmark(
                (moving_ankle_x if dominant_side == "RIGHT" else static_ankle_x) - 0.02,
                (moving_ankle_y if dominant_side == "RIGHT" else static_ankle_y) + 0.04,
            ),
        }
        frames.append(
            PoseFrameResponse(
                session_id=UUID(session_id),
                frame_index=frame_index,
                timestamp_ms=frame_index * 33.333,
                landmarks=landmarks,
                frame_valid=True,
                diagnostic_flags=[],
            )
        )
    return frames


def _basic_shooting_pose_frames(
    session_id: str,
    frame_count: int = 46,
    dominant_side: str = "RIGHT",
) -> list[PoseFrameResponse]:
    frames: list[PoseFrameResponse] = []
    for frame_index in range(frame_count):
        if frame_index < 10:
            progress = 0.0
        elif frame_index < 21:
            progress = (frame_index - 9) / 12
        elif frame_index < 32:
            progress = 1.0 - ((frame_index - 21) / 11)
        else:
            progress = -((frame_index - 31) / 14)

        if progress >= 0:
            moving_knee_x = 0.58 + (0.05 * progress)
            moving_knee_y = 0.72
            moving_ankle_x = 0.64 + (0.11 * progress)
            moving_ankle_y = 0.90 - (0.11 * progress)
        else:
            through = min(abs(progress), 1.0)
            moving_knee_x = 0.56 - (0.04 * through)
            moving_knee_y = 0.72
            moving_ankle_x = 0.47 - (0.15 * through)
            moving_ankle_y = 0.90 - (0.10 * through)

        shoulder_shift = 0.01 * max(-progress, 0.0)
        static_knee_x = 0.43 if dominant_side == "RIGHT" else 0.57
        static_knee_y = 0.73
        static_ankle_x = 0.43 if dominant_side == "RIGHT" else 0.57
        static_ankle_y = 0.90
        landmarks = {
            "nose": _landmark(0.50 + shoulder_shift, 0.22),
            "left_shoulder": _landmark(0.42 + shoulder_shift, 0.34),
            "right_shoulder": _landmark(0.58 + shoulder_shift, 0.34),
            "left_elbow": _landmark(0.39 + shoulder_shift, 0.48),
            "right_elbow": _landmark(0.61 + shoulder_shift, 0.48),
            "left_wrist": _landmark(0.38 + shoulder_shift, 0.60),
            "right_wrist": _landmark(0.62 + shoulder_shift, 0.60),
            "left_hip": _landmark(0.45, 0.56),
            "right_hip": _landmark(0.55, 0.56),
            "left_knee": _landmark(
                moving_knee_x if dominant_side == "LEFT" else static_knee_x,
                moving_knee_y if dominant_side == "LEFT" else static_knee_y,
            ),
            "right_knee": _landmark(
                moving_knee_x if dominant_side == "RIGHT" else static_knee_x,
                moving_knee_y if dominant_side == "RIGHT" else static_knee_y,
            ),
            "left_ankle": _landmark(
                moving_ankle_x if dominant_side == "LEFT" else static_ankle_x,
                moving_ankle_y if dominant_side == "LEFT" else static_ankle_y,
            ),
            "right_ankle": _landmark(
                moving_ankle_x if dominant_side == "RIGHT" else static_ankle_x,
                moving_ankle_y if dominant_side == "RIGHT" else static_ankle_y,
            ),
            "left_heel": _landmark(0.41, 0.92),
            "right_heel": _landmark(
                (moving_ankle_x if dominant_side == "RIGHT" else static_ankle_x) + 0.02,
                (moving_ankle_y if dominant_side == "RIGHT" else static_ankle_y) + 0.02,
            ),
            "left_foot_index": _landmark(0.45, 0.94),
            "right_foot_index": _landmark(
                (moving_ankle_x if dominant_side == "RIGHT" else static_ankle_x) - 0.02,
                (moving_ankle_y if dominant_side == "RIGHT" else static_ankle_y) + 0.04,
            ),
        }
        frames.append(
            PoseFrameResponse(
                session_id=UUID(session_id),
                frame_index=frame_index,
                timestamp_ms=frame_index * 33.333,
                landmarks=landmarks,
                frame_valid=True,
                diagnostic_flags=[],
            )
        )
    return frames


def test_phase2a_segmentation_registry_covers_rollout_drills() -> None:
    assert {
        "bodyweight_squat",
        "set_shot_form",
        "dumbbell_shoulder_press",
        "defensive_stance",
        "instep_pass",
        "basic_shooting_form",
    } <= set(SEGMENTATION_REGISTRY)
    assert {contract.drill_id for contract in SUPPORTED_CONTRACTS} <= set(SEGMENTATION_REGISTRY)


def test_phase2a_metric_calculator_registry_covers_contract_metrics() -> None:
    metric_ids = {
        metric.metric_id
        for contract in SUPPORTED_CONTRACTS
        for metric in contract.metric_contracts
    }

    assert metric_ids <= set(METRIC_CALCULATOR_REGISTRY)


def test_phase2a_metric_calculator_uses_contract_parameters() -> None:
    evaluator = Phase2AEvaluator()
    metric = next(
        metric
        for metric in SET_SHOT_FORM_CONTRACT.metric_contracts
        if metric.phase_id == "setup" and metric.metric_id == "posture_accuracy"
    )
    frame = _set_shot_pose_frames("00000000-0000-0000-0000-000000000000", frame_count=1)[0]

    score = evaluator._score_posture_accuracy(metric, [frame], None)

    assert metric.parameters["target_lean_deg"] == 8.0
    assert score == pytest.approx(1 - (8 / 28), abs=0.0001)


def _contract_metric(
    contract,
    *,
    metric_id: str,
    phase_id: str,
) -> MetricContract:
    return next(
        metric
        for metric in contract.metric_contracts
        if metric.metric_id == metric_id and metric.phase_id == phase_id
    )


def test_phase2a_bodyweight_squat_repetition_consistency_is_bilateral_symmetry() -> None:
    evaluator = Phase2AEvaluator()
    metric = _contract_metric(
        BODYWEIGHT_SQUAT_CONTRACT,
        metric_id="repetition_consistency",
        phase_id="ascent",
    )
    frame = _squat_pose_frames("00000000-0000-0000-0000-000000000000", frame_count=1)[0]

    clean_single_rep_score = evaluator._score_repetition_consistency(
        metric,
        [frame],
        None,
    )
    landmarks = dict(frame.landmarks)
    landmarks["right_knee"] = _landmark(0.48, 0.67)
    asymmetric_frame = frame.model_copy(update={"landmarks": landmarks})
    asymmetric_score = evaluator._score_repetition_consistency(
        metric,
        [asymmetric_frame],
        None,
    )

    assert clean_single_rep_score == pytest.approx(1.0, abs=0.0001)
    assert asymmetric_score < metric.ideal_min


def test_phase2a_bodyweight_squat_depth_scores_good_depth_above_shallow_depth() -> None:
    evaluator = Phase2AEvaluator()
    session_id = "00000000-0000-0000-0000-000000000000"
    metric = _contract_metric(
        BODYWEIGHT_SQUAT_CONTRACT,
        metric_id="squat_depth",
        phase_id="descent",
    )
    good_frames = [
        _pose_frame(
            session_id,
            frame_index=0,
            landmarks=_squat_depth_landmarks(left_hip_x=0.35, left_ankle_x=0.45),
        )
    ]
    shallow_frames = [
        _pose_frame(
            session_id,
            frame_index=0,
            landmarks=_squat_depth_landmarks(left_hip_x=0.45, left_ankle_x=0.50),
        )
    ]

    good_result = evaluator._compute_metric_result(
        metric_contract=metric,
        frames=good_frames,
        dominant_side=None,
        level_factor=1.0,
    )
    shallow_result = evaluator._compute_metric_result(
        metric_contract=metric,
        frames=shallow_frames,
        dominant_side=None,
        level_factor=1.0,
    )

    assert good_result.computation_status == ComputationStatus.COMPUTED
    assert shallow_result.computation_status == ComputationStatus.COMPUTED
    assert good_result.normalized_score is not None
    assert shallow_result.normalized_score is not None
    assert good_result.normalized_score >= metric.ideal_min
    assert shallow_result.normalized_score < metric.ideal_min
    assert good_result.normalized_score > shallow_result.normalized_score
    assert good_result.severity_level == SeverityLevel.MINOR
    assert shallow_result.severity_level == SeverityLevel.SEVERE


def test_phase2a_bodyweight_squat_depth_requires_knee_angle_landmarks() -> None:
    evaluator = Phase2AEvaluator()
    metric = _contract_metric(
        BODYWEIGHT_SQUAT_CONTRACT,
        metric_id="squat_depth",
        phase_id="descent",
    )
    frame = _pose_frame(
        "00000000-0000-0000-0000-000000000000",
        frame_index=0,
        landmarks={
            "left_hip": _landmark(0.35, 0.55),
            "right_hip": _landmark(0.65, 0.55),
            "left_knee": _landmark(0.50, 0.70),
            "right_knee": _landmark(0.50, 0.70),
        },
    )

    result = evaluator._compute_metric_result(
        metric_contract=metric,
        frames=[frame],
        dominant_side=None,
        level_factor=1.0,
    )

    assert result.computation_status == ComputationStatus.NOT_COMPUTABLE
    assert "MISSING_REQUIRED_LANDMARKS" in result.diagnostic_flags


def test_phase2a_common_metric_formulas_score_good_inputs_above_bad_inputs() -> None:
    evaluator = Phase2AEvaluator()
    session_id = "00000000-0000-0000-0000-000000000000"
    cases: list[tuple[MetricContract, list[PoseFrameResponse], list[PoseFrameResponse], DominantSide | None]] = []

    set_shot_metric = _contract_metric(
        SET_SHOT_FORM_CONTRACT,
        metric_id="shooting_alignment",
        phase_id="release",
    )
    set_shot_base = _set_shot_pose_frames(session_id, frame_count=1)[0]
    good_set_shot_landmarks = dict(set_shot_base.landmarks)
    good_set_shot_landmarks.update(
        {
            "right_shoulder": _landmark(0.56, 0.36),
            "right_elbow": _landmark(0.56, 0.30),
            "right_wrist": _landmark(0.56, 0.20),
        }
    )
    bad_set_shot_landmarks = dict(good_set_shot_landmarks)
    bad_set_shot_landmarks.update(
        {
            "right_elbow": _landmark(0.74, 0.30),
            "right_wrist": _landmark(0.90, 0.20),
        }
    )
    cases.append(
        (
            set_shot_metric,
            [_pose_frame(session_id, frame_index=0, landmarks=good_set_shot_landmarks)],
            [_pose_frame(session_id, frame_index=0, landmarks=bad_set_shot_landmarks)],
            DominantSide.RIGHT,
        )
    )

    press_metric = _contract_metric(
        DUMBBELL_SHOULDER_PRESS_CONTRACT,
        metric_id="shoulder_symmetry",
        phase_id="lockout",
    )
    press_base = _shoulder_press_pose_frames(session_id, frame_count=1)[0]
    good_press_landmarks = dict(press_base.landmarks)
    bad_press_landmarks = dict(good_press_landmarks)
    bad_press_landmarks["right_wrist"] = _landmark(
        good_press_landmarks["right_wrist"].x,
        good_press_landmarks["right_wrist"].y + 0.18,
    )
    cases.append(
        (
            press_metric,
            [_pose_frame(session_id, frame_index=0, landmarks=good_press_landmarks)],
            [_pose_frame(session_id, frame_index=0, landmarks=bad_press_landmarks)],
            None,
        )
    )

    stance_metric = _contract_metric(
        DEFENSIVE_STANCE_CONTRACT,
        metric_id="stance_width_control",
        phase_id="hold",
    )
    good_stance_landmarks = {
        "left_shoulder": _landmark(0.40, 0.30),
        "right_shoulder": _landmark(0.60, 0.30),
        "left_ankle": _landmark(0.37, 0.90),
        "right_ankle": _landmark(0.63, 0.90),
    }
    bad_stance_landmarks = {
        **good_stance_landmarks,
        "left_ankle": _landmark(0.47, 0.90),
        "right_ankle": _landmark(0.53, 0.90),
    }
    cases.append(
        (
            stance_metric,
            [_pose_frame(session_id, frame_index=0, landmarks=good_stance_landmarks)],
            [_pose_frame(session_id, frame_index=0, landmarks=bad_stance_landmarks)],
            None,
        )
    )

    instep_metric = _contract_metric(
        INSTEP_PASS_CONTRACT,
        metric_id="instep_contact_extension",
        phase_id="contact",
    )
    good_instep_landmarks = {
        "right_hip": _landmark(0.50, 0.30),
        "right_knee": _landmark(0.50, 0.52),
        "right_ankle": _landmark(0.56, 0.74),
        "left_hip": _landmark(0.44, 0.30),
        "left_knee": _landmark(0.44, 0.52),
        "left_ankle": _landmark(0.44, 0.74),
    }
    bad_instep_landmarks = {
        **good_instep_landmarks,
        "right_ankle": _landmark(0.72, 0.52),
    }
    cases.append(
        (
            instep_metric,
            [_pose_frame(session_id, frame_index=0, landmarks=good_instep_landmarks)],
            [_pose_frame(session_id, frame_index=0, landmarks=bad_instep_landmarks)],
            DominantSide.RIGHT,
        )
    )

    shooting_metric = _contract_metric(
        BASIC_SHOOTING_FORM_CONTRACT,
        metric_id="shooting_swing_velocity",
        phase_id="swing",
    )
    good_shooting_frames = [
        _pose_frame(
            session_id,
            frame_index=0,
            landmarks={
                "left_ankle": _landmark(0.42, 0.80),
                "right_ankle": _landmark(0.50, 0.80),
            },
        ),
        _pose_frame(
            session_id,
            frame_index=1,
            landmarks={
                "left_ankle": _landmark(0.42, 0.80),
                "right_ankle": _landmark(0.58, 0.80),
            },
        ),
    ]
    bad_shooting_frames = [
        _pose_frame(
            session_id,
            frame_index=0,
            landmarks={
                "left_ankle": _landmark(0.42, 0.80),
                "right_ankle": _landmark(0.50, 0.80),
            },
        ),
        _pose_frame(
            session_id,
            frame_index=1,
            landmarks={
                "left_ankle": _landmark(0.42, 0.80),
                "right_ankle": _landmark(0.505, 0.80),
            },
        ),
    ]
    cases.append((shooting_metric, good_shooting_frames, bad_shooting_frames, DominantSide.RIGHT))

    for metric, good_frames, bad_frames, dominant_side in cases:
        good_result = evaluator._compute_metric_result(
            metric_contract=metric,
            frames=good_frames,
            dominant_side=dominant_side,
            level_factor=1.0,
        )
        bad_result = evaluator._compute_metric_result(
            metric_contract=metric,
            frames=bad_frames,
            dominant_side=dominant_side,
            level_factor=1.0,
        )

        assert good_result.computation_status == ComputationStatus.COMPUTED, metric.metric_id
        assert bad_result.computation_status == ComputationStatus.COMPUTED, metric.metric_id
        assert good_result.normalized_score is not None
        assert bad_result.normalized_score is not None
        assert good_result.normalized_score > bad_result.normalized_score
        assert good_result.normalized_score >= metric.ideal_min
    assert bad_result.normalized_score < metric.ideal_min


def test_phase2a_defensive_stance_segments_low_motion_athletic_stance() -> None:
    evaluator = Phase2AEvaluator()
    ranges = evaluator._segment_defensive_stance(
        _defensive_stance_low_motion_frames("00000000-0000-0000-0000-000000000000"),
        parameters=DEFENSIVE_STANCE_CONTRACT.segmentation_parameters,
    )

    assert [phase.phase_id for phase in ranges] == ["setup", "hold", "recovery"]
    assert ranges[0].start_frame_index == 0
    assert ranges[-1].end_frame_index == 9
    assert ranges[0].end_frame_index <= ranges[1].start_frame_index
    assert ranges[1].end_frame_index <= ranges[2].start_frame_index


def test_phase2a_defensive_stance_rejects_fully_static_clip() -> None:
    evaluator = Phase2AEvaluator()
    frames = _defensive_stance_low_motion_frames("00000000-0000-0000-0000-000000000000")
    static_frames = [
        frame.model_copy(
            update={
                "landmarks": {
                    **frame.landmarks,
                    "left_knee": _landmark(0.498, 0.74),
                    "right_knee": _landmark(0.502, 0.74),
                }
            }
        )
        for frame in frames
    ]

    with pytest.raises(PhaseSegmentationError, match="Knee-angle motion is too small"):
        evaluator._segment_defensive_stance(
            static_frames,
            parameters=DEFENSIVE_STANCE_CONTRACT.segmentation_parameters,
        )


def test_phase2a_single_rep_squat_keeps_single_cycle_fallback_metadata(
    client,
    db_session,
) -> None:
    token = _register_user(client, email="single-rep-squat@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(
        client,
        token,
        drill=drill,
        skill_level="BEGINNER",
        camera_view="RIGHT_SAGITTAL",
    )
    _store_pose_sequence(
        db_session,
        session_id=session["id"],
        frames=_squat_depth_cycle_frames(session["id"], start_frame_index=0),
    )

    response = client.post(
        f"/api/sessions/{session['id']}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert payload["detected_rep_count"] == 1
    assert payload["evaluated_rep_count"] == 1
    assert len(payload["rep_summaries"]) == 1
    assert payload["set_level_summary"]["evaluation_mode"] == "single_cycle"
    assert payload["set_level_summary"]["consistency_score"] == 1.0
    assert "REP_DETECTION_FALLBACK_SINGLE_DOMINANT_CYCLE" in payload["diagnostic_flags"]
    assert "MULTI_REP_EVALUATION" not in payload["diagnostic_flags"]


def test_phase2a_noisy_low_motion_squat_does_not_hallucinate_reps() -> None:
    evaluator = Phase2AEvaluator()
    session_id = "00000000-0000-0000-0000-000000000000"
    frames = [
        _pose_frame(
            session_id,
            frame_index=frame_index,
            landmarks=_squat_depth_landmarks(
                left_hip_x=0.445 + (0.003 if frame_index % 2 else 0.0),
                left_ankle_x=0.50,
            ),
        )
        for frame_index in range(14)
    ]

    cycles = evaluator._detect_rep_cycles(
        contract=BODYWEIGHT_SQUAT_CONTRACT,
        frames=frames,
        dominant_side=None,
    )

    assert cycles == []


def test_phase2a_multi_rep_squat_set_aggregates_reps(client, db_session) -> None:
    token = _register_user(client, email="multi-rep-squat@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(
        client,
        token,
        drill=drill,
        skill_level="BEGINNER",
        camera_view="RIGHT_SAGITTAL",
    )
    _store_pose_sequence(
        db_session,
        session_id=session["id"],
        frames=_multi_rep_squat_depth_frames(session["id"], pattern=["good", "good", "good"]),
    )

    response = client.post(
        f"/api/sessions/{session['id']}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert payload["detected_rep_count"] == 3
    assert payload["evaluated_rep_count"] == 3
    assert len(payload["rep_summaries"]) == 3
    assert payload["set_level_summary"]["evaluation_mode"] == "multi_rep"
    assert payload["set_level_summary"]["average_score"] == payload["overall_score"]
    assert "MULTI_REP_EVALUATION" in payload["diagnostic_flags"]
    assert "DETECTED_REPS:3" in payload["diagnostic_flags"]
    assert "EVALUATED_REPS:3" in payload["diagnostic_flags"]


def test_phase2a_one_shallow_squat_among_good_reps_flags_consistency(
    client,
    db_session,
) -> None:
    token = _register_user(client, email="multi-rep-shallow-squat@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(
        client,
        token,
        drill=drill,
        skill_level="BEGINNER",
        camera_view="RIGHT_SAGITTAL",
    )
    _store_pose_sequence(
        db_session,
        session_id=session["id"],
        frames=_multi_rep_squat_depth_frames(session["id"], pattern=["good", "shallow", "good"]),
    )

    response = client.post(
        f"/api/sessions/{session['id']}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    set_summary = payload["set_level_summary"]
    assert payload["status"] == "COMPLETED"
    assert payload["evaluated_rep_count"] == 3
    assert set_summary["evaluation_mode"] == "multi_rep"
    assert set_summary["consistency_score"] < 0.75
    assert set_summary["consistency_warning"]
    assert "REP_CONSISTENCY_WARNING" in payload["diagnostic_flags"]


def test_phase2a_shoulder_press_multi_rep_set_detects_reps(client, db_session) -> None:
    token = _register_user(client, email="multi-rep-press@example.com")
    drill = _get_drill(db_session, "Dumbbell Shoulder Press")
    session = _create_session(
        client,
        token,
        drill=drill,
        skill_level="BEGINNER",
        camera_view="FRONTAL",
    )
    _store_pose_sequence(
        db_session,
        session_id=session["id"],
        frames=_multi_rep_shoulder_press_frames(session["id"], rep_count=2),
    )

    response = client.post(
        f"/api/sessions/{session['id']}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert payload["detected_rep_count"] == 2
    assert payload["evaluated_rep_count"] == 2
    assert payload["set_level_summary"]["evaluation_mode"] == "multi_rep"


def test_phase2a_defensive_stance_multi_cycle_supported(client, db_session) -> None:
    token = _register_user(client, email="multi-cycle-stance@example.com")
    drill = _get_drill(db_session, "Defensive Stance")
    session = _create_session(
        client,
        token,
        drill=drill,
        skill_level="BEGINNER",
        camera_view="FRONTAL",
    )
    _store_pose_sequence(
        db_session,
        session_id=session["id"],
        frames=_multi_cycle_defensive_stance_frames(session["id"], cycle_count=2),
    )

    response = client.post(
        f"/api/sessions/{session['id']}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert payload["detected_rep_count"] == 2
    assert payload["evaluated_rep_count"] == 2
    assert payload["set_level_summary"]["evaluation_mode"] == "multi_rep"


def test_phase2a_segmentation_uses_contract_parameters() -> None:
    evaluator = Phase2AEvaluator()
    contract = replace(
        BODYWEIGHT_SQUAT_CONTRACT,
        segmentation_parameters={
            **BODYWEIGHT_SQUAT_CONTRACT.segmentation_parameters,
            "min_knee_motion_delta_deg": 999.0,
        },
    )

    with pytest.raises(PhaseSegmentationError, match="Knee-angle motion is too small"):
        evaluator._segment_phases(
            contract=contract,
            frames=_squat_pose_frames("00000000-0000-0000-0000-000000000000"),
            dominant_side=None,
        )


def test_phase2a_unknown_metric_is_not_computable() -> None:
    evaluator = Phase2AEvaluator()
    metric = MetricContract(
        metric_id="unknown_metric",
        metric_name="unknown_metric",
        phase_id="setup",
        description="Unsupported metric for registry safety test.",
        required_landmarks=("left_hip", "right_hip"),
        computation="unsupported",
        parameters={},
        range_type="closed_range",
        ideal_min=0.8,
        ideal_max=1.0,
        unit="score",
        base_moderate_deviation=0.1,
        base_severe_deviation=0.2,
        affected_body_part="unknown",
    )
    frame = _squat_pose_frames("00000000-0000-0000-0000-000000000000", frame_count=1)[0]

    result = evaluator._compute_metric_result(
        metric_contract=metric,
        frames=[frame],
        dominant_side=None,
        level_factor=1.0,
    )

    assert result.computation_status == ComputationStatus.NOT_COMPUTABLE
    assert result.raw_value is None
    assert "UNSUPPORTED_METRIC_CALCULATOR" in result.diagnostic_flags
    assert evaluator._is_diagnostic_issue(result) is True
    issue = evaluator._build_issue(result)
    assert issue.computation_status == ComputationStatus.NOT_COMPUTABLE
    assert issue.diagnostic_flags == result.diagnostic_flags


def test_phase2a_api_response_includes_null_metric_fields_for_not_computable(
    client,
    db_session,
    monkeypatch,
) -> None:
    token = _register_user(client, email="stable-null-shape@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(
        client,
        token,
        drill=drill,
        skill_level="BEGINNER",
        camera_view="RIGHT_SAGITTAL",
    )
    _store_pose_sequence(
        db_session,
        session_id=session["id"],
        frames=_squat_pose_frames(session["id"]),
    )
    monkeypatch.delitem(METRIC_CALCULATOR_REGISTRY, "hip_stability")

    response = client.post(
        f"/api/sessions/{session['id']}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    metric = next(
        metric
        for phase in payload["phase_results"]
        for metric in phase["metric_results"]
        if metric["metric_id"] == "hip_stability"
    )
    assert metric["computation_status"] == "NOT_COMPUTABLE"
    assert "raw_value" in metric
    assert "normalized_score" in metric
    assert "deviation" in metric
    assert metric["raw_value"] is None
    assert metric["normalized_score"] is None
    assert metric["deviation"] is None


def test_left_sagittal_normalization_swaps_canonical_landmarks() -> None:
    session_id = "00000000-0000-0000-0000-000000000000"
    pose_sequence = _pose_sequence(session_id, _squat_pose_frames(session_id, frame_count=1))
    original_frame = pose_sequence.sequence_data[0]

    normalized = normalize_pose_sequence_for_camera_view(
        pose_sequence=pose_sequence,
        camera_view=CameraView.LEFT_SAGITTAL,
    )
    normalized_frame = normalized.sequence_data[0]

    assert normalized_frame.landmarks["left_shoulder"] == original_frame.landmarks["right_shoulder"]
    assert normalized_frame.landmarks["right_shoulder"] == original_frame.landmarks["left_shoulder"]
    assert normalized_frame.landmarks["left_knee"] == original_frame.landmarks["right_knee"]
    assert normalized_frame.landmarks["right_knee"] == original_frame.landmarks["left_knee"]
    assert normalized_frame.landmarks["nose"] == original_frame.landmarks["nose"]
    assert original_frame.landmarks["left_shoulder"].x == 0.43


def test_non_left_camera_views_do_not_normalize_pose_sequence() -> None:
    session_id = "00000000-0000-0000-0000-000000000000"
    pose_sequence = _pose_sequence(session_id, _set_shot_pose_frames(session_id, frame_count=1))

    assert (
        normalize_pose_sequence_for_camera_view(
            pose_sequence=pose_sequence,
            camera_view=CameraView.RIGHT_SAGITTAL,
        )
        is pose_sequence
    )
    assert (
        normalize_pose_sequence_for_camera_view(
            pose_sequence=pose_sequence,
            camera_view=CameraView.FRONTAL,
        )
        is pose_sequence
    )


def test_dominant_side_detector_prefers_ankle_motion_for_leg_dominant_drills(
    db_session,
) -> None:
    detector = DominantSideDetector()
    drill = _get_drill(db_session, "Instep Pass")
    session_id = "00000000-0000-0000-0000-000000000101"

    result = detector.detect(
        drill=drill,
        pose_sequence=_pose_sequence(
            session_id,
            _instep_pass_pose_frames(session_id, dominant_side="LEFT"),
        ),
    )

    assert result.resolved_side == DominantSide.LEFT
    assert result.confidence > 0
    assert result.method == "ankle_motion"


def test_dominant_side_detector_prefers_wrist_motion_for_arm_dominant_drills(
    db_session,
) -> None:
    detector = DominantSideDetector()
    drill = _get_drill(db_session, "Set Shot Form")
    session_id = "00000000-0000-0000-0000-000000000102"

    result = detector.detect(
        drill=drill,
        pose_sequence=_pose_sequence(
            session_id,
            _set_shot_pose_frames(session_id, dominant_side="LEFT"),
        ),
    )

    assert result.resolved_side == DominantSide.LEFT
    assert result.confidence > 0
    assert result.method == "wrist_motion"


def test_dominant_side_detector_reports_insufficient_evidence(db_session) -> None:
    detector = DominantSideDetector()
    drill = _get_drill(db_session, "Set Shot Form")
    session_id = "00000000-0000-0000-0000-000000000103"

    result = detector.detect(
        drill=drill,
        pose_sequence=_pose_sequence(
            session_id,
            _set_shot_pose_frames(session_id, frame_count=2),
        ),
    )

    assert result.resolved_side is None
    assert result.method == "insufficient_evidence"
    assert "INSUFFICIENT_VISIBLE_SIDE_SAMPLES" in result.diagnostic_flags


def test_left_sagittal_evaluation_matches_canonical_right_sagittal(
    client,
    db_session,
) -> None:
    token = _register_user(client, email="left-sagittal-equivalence@example.com")
    drill = _get_drill(db_session, "Instep Pass")
    right_session = _create_session(
        client,
        token,
        drill=drill,
        skill_level="BEGINNER",
        camera_view="RIGHT_SAGITTAL",
    )
    left_session = _create_session(
        client,
        token,
        drill=drill,
        skill_level="BEGINNER",
        camera_view="LEFT_SAGITTAL",
    )
    _store_pose_sequence(
        db_session,
        session_id=right_session["id"],
        frames=_instep_pass_pose_frames(right_session["id"]),
    )
    _store_pose_sequence(
        db_session,
        session_id=left_session["id"],
        frames=_swap_sagittal_landmarks(_instep_pass_pose_frames(left_session["id"])),
    )

    right_response = client.post(
        f"/api/sessions/{right_session['id']}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )
    left_response = client.post(
        f"/api/sessions/{left_session['id']}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert right_response.status_code == 200
    assert left_response.status_code == 200
    right_payload = right_response.json()
    left_payload = left_response.json()
    assert right_payload["status"] == "COMPLETED"
    assert left_payload["status"] == "COMPLETED"
    assert right_payload["overall_score"] == left_payload["overall_score"]
    assert [
        (phase["phase_id"], metric["metric_id"], metric["raw_value"], metric["normalized_score"])
        for phase in right_payload["phase_results"]
        for metric in phase["metric_results"]
    ] == [
        (phase["phase_id"], metric["metric_id"], metric["raw_value"], metric["normalized_score"])
        for phase in left_payload["phase_results"]
        for metric in phase["metric_results"]
    ]


def test_phase2a_auto_detect_failure_does_not_silently_default_right(
    client,
    db_session,
) -> None:
    token = _register_user(client, email="auto-detect-failure@example.com")
    drill = _get_drill(db_session, "Set Shot Form")
    session = _create_session(
        client,
        token,
        drill=drill,
        skill_level="BEGINNER",
        camera_view="FRONTAL",
    )
    _store_pose_sequence(
        db_session,
        session_id=session["id"],
        frames=_set_shot_pose_frames(session["id"], frame_count=2),
    )

    response = client.post(
        f"/api/sessions/{session['id']}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "INSUFFICIENT_DATA"
    assert "DOMINANT_SIDE_RESOLUTION_FAILED" in payload["diagnostic_flags"]
    assert "resolved_dominant_side" not in payload
    assert "AUTO_DETECTED_DOMINANT_SIDE:RIGHT" not in payload["diagnostic_flags"]


@pytest.mark.parametrize("dominant_side", ["LEFT", "RIGHT"])
def test_phase2a_manual_dominant_side_bypasses_auto_detection(
    client,
    db_session,
    monkeypatch,
    dominant_side: str,
) -> None:
    token = _register_user(client, email=f"manual-{dominant_side.lower()}@example.com")
    drill = _get_drill(db_session, "Instep Pass")
    session = _create_session(
        client,
        token,
        drill=drill,
        skill_level="INTERMEDIATE",
        camera_view="RIGHT_SAGITTAL",
        dominant_side=dominant_side,
    )
    _store_pose_sequence(
        db_session,
        session_id=session["id"],
        frames=_instep_pass_pose_frames(session["id"], dominant_side=dominant_side),
    )

    def fail_detect(self, **kwargs):
        raise AssertionError("Auto-detection should not run for manual dominant_side.")

    monkeypatch.setattr(DominantSideDetector, "detect", fail_detect)

    response = client.post(
        f"/api/sessions/{session['id']}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert payload["requested_dominant_side"] == dominant_side
    assert payload["resolved_dominant_side"] == dominant_side
    assert "dominant_side_confidence" not in payload


def test_phase2a_evaluation_uses_auto_detected_side_for_arm_dominant_drills(
    client,
    db_session,
) -> None:
    token = _register_user(client, email="auto-detect-resolution@example.com")
    drill = _get_drill(db_session, "Set Shot Form")
    auto_session = _create_session(
        client,
        token,
        drill=drill,
        skill_level="BEGINNER",
        camera_view="FRONTAL",
    )
    manual_session = _create_session(
        client,
        token,
        drill=drill,
        skill_level="BEGINNER",
        camera_view="FRONTAL",
        dominant_side="RIGHT",
    )
    _store_pose_sequence(
        db_session,
        session_id=auto_session["id"],
        frames=_set_shot_pose_frames(auto_session["id"], dominant_side="RIGHT"),
    )
    _store_pose_sequence(
        db_session,
        session_id=manual_session["id"],
        frames=_set_shot_pose_frames(manual_session["id"], dominant_side="RIGHT"),
    )

    auto_response = client.post(
        f"/api/sessions/{auto_session['id']}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )
    manual_response = client.post(
        f"/api/sessions/{manual_session['id']}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert auto_response.status_code == 200
    assert manual_response.status_code == 200
    auto_payload = auto_response.json()
    manual_payload = manual_response.json()
    assert auto_payload["status"] == "COMPLETED"
    assert manual_payload["status"] == "COMPLETED"
    assert auto_payload["resolved_dominant_side"] == "RIGHT"
    assert auto_payload["dominant_side_confidence"] > 0
    assert "requested_dominant_side" not in auto_payload
    assert manual_payload["requested_dominant_side"] == "RIGHT"
    assert manual_payload["resolved_dominant_side"] == "RIGHT"
    assert auto_payload["overall_score"] == manual_payload["overall_score"]
    assert [
        (phase["phase_id"], metric["metric_id"], metric["raw_value"], metric["normalized_score"])
        for phase in auto_payload["phase_results"]
        for metric in phase["metric_results"]
    ] == [
        (phase["phase_id"], metric["metric_id"], metric["raw_value"], metric["normalized_score"])
        for phase in manual_payload["phase_results"]
        for metric in phase["metric_results"]
    ]


@pytest.mark.parametrize("skill_level", ["BEGINNER", "INTERMEDIATE", "ADVANCED"])
def test_phase2a_bodyweight_squat_evaluates_all_skill_levels(
    client,
    db_session,
    skill_level: str,
) -> None:
    token = _register_user(client, email=f"squat-{skill_level.lower()}@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(
        client,
        token,
        drill=drill,
        skill_level=skill_level,
        camera_view="RIGHT_SAGITTAL",
    )
    _store_pose_sequence(
        db_session,
        session_id=session["id"],
        frames=_squat_pose_frames(session["id"]),
    )

    response = client.post(
        f"/api/sessions/{session['id']}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert "requested_dominant_side" not in payload
    assert "resolved_dominant_side" not in payload
    assert payload["evaluation_version"] == EXPECTED_EVALUATION_VERSION
    assert payload["skill_level"] == skill_level
    assert [phase["phase_id"] for phase in payload["phase_results"]] == [
        "setup",
        "descent",
        "ascent",
    ]
    _assert_stable_evaluation_artifact_shape(
        payload,
        expected_phases=["setup", "descent", "ascent"],
    )
    assert payload["overall_score"] > 0
    assert payload["strongest_metrics"]
    assert payload["weakest_metrics"]
    assert set(payload["strongest_metrics"][0]) == {
        "phase_id",
        "metric_id",
        "metric_name",
        "score",
    }

    ranges = [phase["frame_range"] for phase in payload["phase_results"]]
    assert {phase_range["boundary_mode"] for phase_range in ranges} == {
        "inclusive_overlapping"
    }
    assert ranges[0]["start_frame_index"] == 0
    assert ranges[0]["end_frame_index"] == ranges[1]["start_frame_index"]
    assert ranges[1]["end_frame_index"] == ranges[2]["start_frame_index"]
    assert ranges[0]["end_frame_index"] <= ranges[1]["end_frame_index"]
    assert ranges[1]["end_frame_index"] <= ranges[2]["end_frame_index"]

    rows = list(
        db_session.scalars(
            select(MetricResult).where(MetricResult.session_id == session["id"])
        )
    )
    assert len(rows) == sum(len(phase["metric_results"]) for phase in payload["phase_results"])
    assert rows
    assert {row.formula_version for row in rows} == {"phase0_v0_1_0"}
    assert {row.phase_id for row in rows} == {"setup", "descent", "ascent"}


@pytest.mark.parametrize("skill_level", ["BEGINNER", "INTERMEDIATE", "ADVANCED"])
def test_phase2a_set_shot_form_evaluates_all_skill_levels(
    client,
    db_session,
    skill_level: str,
) -> None:
    token = _register_user(client, email=f"set-shot-{skill_level.lower()}@example.com")
    drill = _get_drill(db_session, "Set Shot Form")
    session = _create_session(
        client,
        token,
        drill=drill,
        skill_level=skill_level,
        camera_view="FRONTAL",
        dominant_side="RIGHT",
    )
    _store_pose_sequence(
        db_session,
        session_id=session["id"],
        frames=_set_shot_pose_frames(session["id"]),
    )

    response = client.post(
        f"/api/sessions/{session['id']}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert payload["evaluation_version"] == EXPECTED_EVALUATION_VERSION
    assert payload["skill_level"] == skill_level
    assert [phase["phase_id"] for phase in payload["phase_results"]] == [
        "setup",
        "load",
        "release",
        "follow_through",
    ]
    _assert_stable_evaluation_artifact_shape(
        payload,
        expected_phases=["setup", "load", "release", "follow_through"],
    )
    assert payload["overall_score"] > 0
    assert all(
        phase["frame_range"]["boundary_mode"] == "inclusive_overlapping"
        for phase in payload["phase_results"]
    )
    assert payload["strongest_metrics"][0]["metric_id"]

    rows = list(
        db_session.scalars(
            select(MetricResult).where(MetricResult.session_id == session["id"])
        )
    )
    assert rows
    assert {row.phase_id for row in rows} == {
        "setup",
        "load",
        "release",
        "follow_through",
    }


@pytest.mark.parametrize("skill_level", ["BEGINNER", "INTERMEDIATE", "ADVANCED"])
def test_phase2b_dumbbell_shoulder_press_evaluates_all_skill_levels(
    client,
    db_session,
    skill_level: str,
) -> None:
    token = _register_user(client, email=f"shoulder-press-{skill_level.lower()}@example.com")
    drill = _get_drill(db_session, "Dumbbell Shoulder Press")
    session = _create_session(
        client,
        token,
        drill=drill,
        skill_level=skill_level,
        camera_view="FRONTAL",
    )
    _store_pose_sequence(
        db_session,
        session_id=session["id"],
        frames=_shoulder_press_pose_frames(session["id"]),
    )

    response = client.post(
        f"/api/sessions/{session['id']}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert payload["skill_level"] == skill_level
    _assert_stable_evaluation_artifact_shape(
        payload,
        expected_phases=["setup", "press", "lockout", "return"],
    )
    ranges = [phase["frame_range"] for phase in payload["phase_results"]]
    assert ranges[0]["end_frame_index"] == ranges[1]["start_frame_index"]
    assert ranges[1]["end_frame_index"] == ranges[2]["start_frame_index"]
    assert ranges[2]["end_frame_index"] == ranges[3]["start_frame_index"]

    rows = list(
        db_session.scalars(
            select(MetricResult).where(MetricResult.session_id == session["id"])
        )
    )
    assert rows
    assert {row.phase_id for row in rows} == {"setup", "press", "lockout", "return"}
    assert {row.formula_version for row in rows} == {"phase0_v0_1_0"}


@pytest.mark.parametrize("skill_level", ["BEGINNER", "INTERMEDIATE", "ADVANCED"])
def test_phase2b_defensive_stance_evaluates_all_skill_levels(
    client,
    db_session,
    skill_level: str,
) -> None:
    token = _register_user(client, email=f"defensive-stance-{skill_level.lower()}@example.com")
    drill = _get_drill(db_session, "Defensive Stance")
    session = _create_session(
        client,
        token,
        drill=drill,
        skill_level=skill_level,
        camera_view="FRONTAL",
    )
    _store_pose_sequence(
        db_session,
        session_id=session["id"],
        frames=_defensive_stance_pose_frames(session["id"]),
    )

    response = client.post(
        f"/api/sessions/{session['id']}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert payload["skill_level"] == skill_level
    _assert_stable_evaluation_artifact_shape(
        payload,
        expected_phases=["setup", "hold", "recovery"],
    )
    ranges = [phase["frame_range"] for phase in payload["phase_results"]]
    assert ranges[0]["end_frame_index"] == ranges[1]["start_frame_index"]
    assert ranges[1]["end_frame_index"] == ranges[2]["start_frame_index"]

    rows = list(
        db_session.scalars(
            select(MetricResult).where(MetricResult.session_id == session["id"])
        )
    )
    assert rows
    assert {row.phase_id for row in rows} == {"setup", "hold", "recovery"}
    assert {row.formula_version for row in rows} == {"phase0_v0_1_0"}


@pytest.mark.parametrize("skill_level", ["BEGINNER", "INTERMEDIATE", "ADVANCED"])
def test_phase2c_instep_pass_evaluates_all_skill_levels(
    client,
    db_session,
    skill_level: str,
) -> None:
    token = _register_user(client, email=f"instep-pass-{skill_level.lower()}@example.com")
    drill = _get_drill(db_session, "Instep Pass")
    session = _create_session(
        client,
        token,
        drill=drill,
        skill_level=skill_level,
        camera_view="RIGHT_SAGITTAL",
    )
    _store_pose_sequence(
        db_session,
        session_id=session["id"],
        frames=_instep_pass_pose_frames(session["id"]),
    )

    response = client.post(
        f"/api/sessions/{session['id']}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert payload["skill_level"] == skill_level
    _assert_stable_evaluation_artifact_shape(
        payload,
        expected_phases=["setup", "backswing", "contact", "follow_through"],
    )
    ranges = [phase["frame_range"] for phase in payload["phase_results"]]
    assert ranges[0]["end_frame_index"] == ranges[1]["start_frame_index"]
    assert ranges[1]["end_frame_index"] == ranges[2]["start_frame_index"]
    assert ranges[2]["end_frame_index"] == ranges[3]["start_frame_index"]

    rows = list(
        db_session.scalars(
            select(MetricResult).where(MetricResult.session_id == session["id"])
        )
    )
    assert rows
    assert {row.phase_id for row in rows} == {
        "setup",
        "backswing",
        "contact",
        "follow_through",
    }
    assert {row.formula_version for row in rows} == {"phase0_v0_1_0"}


@pytest.mark.parametrize("skill_level", ["BEGINNER", "INTERMEDIATE", "ADVANCED"])
def test_phase2c_basic_shooting_form_evaluates_all_skill_levels(
    client,
    db_session,
    skill_level: str,
) -> None:
    token = _register_user(client, email=f"basic-shooting-{skill_level.lower()}@example.com")
    drill = _get_drill(db_session, "Basic Shooting Form")
    session = _create_session(
        client,
        token,
        drill=drill,
        skill_level=skill_level,
        camera_view="RIGHT_SAGITTAL",
    )
    _store_pose_sequence(
        db_session,
        session_id=session["id"],
        frames=_basic_shooting_pose_frames(session["id"]),
    )

    response = client.post(
        f"/api/sessions/{session['id']}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert payload["skill_level"] == skill_level
    _assert_stable_evaluation_artifact_shape(
        payload,
        expected_phases=["setup", "load", "swing", "contact", "follow_through"],
    )
    ranges = [phase["frame_range"] for phase in payload["phase_results"]]
    assert ranges[0]["end_frame_index"] == ranges[1]["start_frame_index"]
    assert ranges[1]["end_frame_index"] == ranges[2]["start_frame_index"]
    assert ranges[2]["end_frame_index"] == ranges[3]["start_frame_index"]
    assert ranges[3]["end_frame_index"] == ranges[4]["start_frame_index"]

    rows = list(
        db_session.scalars(
            select(MetricResult).where(MetricResult.session_id == session["id"])
        )
    )
    assert rows
    assert {row.phase_id for row in rows} == {
        "setup",
        "load",
        "swing",
        "contact",
        "follow_through",
    }
    assert {row.formula_version for row in rows} == {"phase0_v0_1_0"}


def test_phase2a_rejects_unsupported_drill_cleanly(client, db_session) -> None:
    token = _register_user(client, email="unsupported-drill@example.com")
    football_drill = _get_drill(db_session, "Instep Pass")
    drill = Drill(
        sport_id=football_drill.sport_id,
        drill_name="Unsupported Cone Drill",
        description="Synthetic unsupported drill for evaluator error handling.",
        reference_payload={},
        coaching_rules={},
        target_metrics={},
    )
    db_session.add(drill)
    db_session.commit()
    db_session.refresh(drill)
    session = _create_session(
        client,
        token,
        drill=drill,
        skill_level="BEGINNER",
    )
    _store_pose_sequence(
        db_session,
        session_id=session["id"],
        frames=_squat_pose_frames(session["id"]),
    )

    response = client.post(
        f"/api/sessions/{session['id']}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "FAILED"
    assert payload["evaluation_version"] == EXPECTED_EVALUATION_VERSION
    assert payload["diagnostic_flags"] == ["UNSUPPORTED_DRILL"]
    rows = list(
        db_session.scalars(
            select(MetricResult).where(MetricResult.session_id == session["id"])
        )
    )
    assert rows == []


def test_phase2a_missing_pose_artifact_returns_structured_failure(client, db_session) -> None:
    token = _register_user(client, email="missing-pose@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(
        client,
        token,
        drill=drill,
        skill_level="BEGINNER",
        camera_view="RIGHT_SAGITTAL",
    )

    response = client.post(
        f"/api/sessions/{session['id']}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "FAILED"
    assert payload["evaluation_version"] == EXPECTED_EVALUATION_VERSION
    assert payload["diagnostic_flags"] == ["MISSING_POSE_SEQUENCE"]
    assert payload["phase_results"] == []


def test_phase2a_reevaluation_clears_stale_feedback_outputs(client, db_session) -> None:
    token = _register_user(client, email="reeval-clears-feedback@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(
        client,
        token,
        drill=drill,
        skill_level="BEGINNER",
        camera_view="RIGHT_SAGITTAL",
    )
    _store_pose_sequence(
        db_session,
        session_id=session["id"],
        frames=_squat_pose_frames(session["id"]),
    )
    db_session.add_all(
        [
            SessionArtifact(
                session_id=UUID(session["id"]),
                artifact_type="feedback_result",
                payload_json={"feedback_version": "stale"},
            ),
            SessionArtifact(
                session_id=UUID(session["id"]),
                artifact_type="llm_feedback_result",
                payload_json={"llm_feedback_version": "stale"},
            ),
        ]
    )
    db_session.add(
        Feedback(
            session_id=UUID(session["id"]),
            severity_level=SeverityLevel.MODERATE,
            technique_issue="stale issue",
            coaching_cue="stale cue",
            metric_snapshot={"source": "stale"},
        )
    )
    db_session.commit()

    response = client.post(
        f"/api/sessions/{session['id']}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"
    stale_artifacts = list(
        db_session.scalars(
            select(SessionArtifact).where(
                SessionArtifact.session_id == session["id"],
                SessionArtifact.artifact_type.in_(
                    ["feedback_result", "llm_feedback_result"]
                ),
            )
        )
    )
    stale_feedback_rows = list(
        db_session.scalars(select(Feedback).where(Feedback.session_id == session["id"]))
    )
    assert stale_artifacts == []
    assert stale_feedback_rows == []

    feedback_response = client.post(
        f"/api/sessions/{session['id']}/feedback",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert feedback_response.status_code == 200
    feedback_payload = feedback_response.json()
    current_feedback_rows = list(
        db_session.scalars(select(Feedback).where(Feedback.session_id == session["id"]))
    )
    assert len(current_feedback_rows) == len(
        feedback_payload["prioritized_feedback_items"]
    )
    assert all(row.technique_issue != "stale issue" for row in current_feedback_rows)
    assert db_session.scalar(
        select(SessionArtifact).where(
            SessionArtifact.session_id == session["id"],
            SessionArtifact.artifact_type == "feedback_result",
        )
    ) is not None


def test_phase2a_real_bodyweight_squat_upload_evaluates(client, db_session) -> None:
    pytest.importorskip("mediapipe")
    asset_path = Path(__file__).resolve().parent / "assets" / "squat1.mov"
    if not asset_path.exists():
        pytest.skip("Repo-local squat1.mov asset is unavailable.")

    token = _register_user(client, email="real-phase2a-squat@example.com")
    drill = _get_drill(db_session, "Bodyweight Squat")
    session = _create_session(
        client,
        token,
        drill=drill,
        skill_level="BEGINNER",
        camera_view="RIGHT_SAGITTAL",
    )

    with asset_path.open("rb") as video_file:
        upload_response = client.post(
            f"/api/sessions/{session['id']}/upload",
            files={"file": (asset_path.name, video_file, "video/quicktime")},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert upload_response.status_code == 200
    assert upload_response.json()["pose_sequence"]["status"] == "COMPLETED"

    evaluation_response = client.post(
        f"/api/sessions/{session['id']}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert evaluation_response.status_code == 200
    payload = evaluation_response.json()
    assert payload["status"] == "COMPLETED"
    assert payload["phase_results"]
    assert payload["overall_score"] > 0
    rows = list(
        db_session.scalars(
            select(MetricResult).where(MetricResult.session_id == session["id"])
        )
    )
    assert rows
