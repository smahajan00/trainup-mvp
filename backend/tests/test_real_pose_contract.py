from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.drill import Drill
from app.models.session_artifact import SessionArtifact

pytest.importorskip("mediapipe")

REQUIRED_PHASE0_KEYPOINTS = {
    "nose",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
}

TEST_ASSET_DIR = Path(__file__).resolve().parent / "assets"

REAL_VIDEO_CANDIDATES = [
    {
        "path": TEST_ASSET_DIR / "squat1.mov",
        "drill_name": "Bodyweight Squat",
        "camera_view": "RIGHT_SAGITTAL",
        "content_type": "video/quicktime",
    },
]


def _resolve_real_video_fixture() -> dict[str, object]:
    for candidate in REAL_VIDEO_CANDIDATES:
        if candidate["path"].exists():
            return candidate
    pytest.skip("No real local human video fixture is available for contract verification.")


def _register_user(client) -> str:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Real Pose Contract",
            "email": "real-pose-contract@example.com",
            "password": "strongpass123",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_real_upload_contract_contains_required_phase0_keypoints(client, db_session) -> None:
    fixture = _resolve_real_video_fixture()
    token = _register_user(client)

    drill = db_session.scalar(
        select(Drill).where(Drill.drill_name == fixture["drill_name"])
    )
    assert drill is not None

    create_payload = {
        "sport_id": str(drill.sport_id),
        "skill_level": "BEGINNER",
        "drill_id": str(drill.id),
        "input_type": "UPLOAD",
        "camera_view": fixture["camera_view"],
    }
    dominant_side = fixture.get("dominant_side")
    if dominant_side is not None:
        create_payload["dominant_side"] = dominant_side

    create_response = client.post(
        "/api/sessions",
        json=create_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_response.status_code == 201
    session_id = create_response.json()["id"]

    video_path = fixture["path"]
    with Path(video_path).open("rb") as fh:
        upload_response = client.post(
            f"/api/sessions/{session_id}/upload",
            files={"file": (Path(video_path).name, fh, fixture["content_type"])},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert upload_response.status_code == 200
    upload_payload = upload_response.json()
    assert upload_payload["pose_sequence"]["status"] == "COMPLETED"

    artifact = db_session.scalar(
        select(SessionArtifact).where(
            SessionArtifact.session_id == session_id,
            SessionArtifact.artifact_type == "pose_sequence",
        )
    )
    assert artifact is not None

    pose_sequence = artifact.payload_json
    valid_frames = [frame for frame in pose_sequence["sequence_data"] if frame["frame_valid"]]
    assert len(valid_frames) >= 3

    for frame in valid_frames[:3]:
        landmark_keys = set(frame["landmarks"].keys())
        missing_keys = sorted(REQUIRED_PHASE0_KEYPOINTS - landmark_keys)
        assert missing_keys == []
