from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.engines.perception_interface.mediapipe_pose_backend import (
    ExtractedPoseFrame,
    ExtractedPoseLandmark,
)
from app.engines.perception_interface.perception_service import PerceptionService


class _FakeVideoCapture:
    def __init__(self, frames: list[object], *, opened: bool = True, fps: float = 30.0) -> None:
        self._frames = list(frames)
        self._opened = opened
        self._fps = fps
        self._position = 0
        self.released = False

    def isOpened(self) -> bool:
        return self._opened

    def read(self) -> tuple[bool, object | None]:
        if self._position >= len(self._frames):
            return False, None

        frame = self._frames[self._position]
        self._position += 1
        return True, frame

    def get(self, prop: int) -> float:
        if prop == 1:
            return self._fps
        if prop == 2:
            return max(self._position - 1, 0) * (1000 / self._fps)
        return 0.0

    def release(self) -> None:
        self.released = True


class _FakeCV2:
    CAP_PROP_FPS = 1
    CAP_PROP_POS_MSEC = 2
    COLOR_BGR2RGB = 3

    def __init__(self, capture: _FakeVideoCapture) -> None:
        self._capture = capture

    def VideoCapture(self, _: str) -> _FakeVideoCapture:
        return self._capture

    @staticmethod
    def cvtColor(frame_bgr: object, _: int) -> object:
        return frame_bgr


class _FakePoseBackend:
    def __init__(self, frames: list[ExtractedPoseFrame]) -> None:
        self._frames = list(frames)
        self._position = 0
        self.closed = False

    def extract(self, *, frame_rgb: object) -> ExtractedPoseFrame:
        del frame_rgb
        frame = self._frames[self._position]
        self._position += 1
        return frame

    def close(self) -> None:
        self.closed = True


def test_extract_pose_sequence_success_applies_ema_smoothing(monkeypatch) -> None:
    service = PerceptionService()
    capture = _FakeVideoCapture(frames=["frame-0", "frame-1"])
    pose_backend = _FakePoseBackend(
        frames=[
            ExtractedPoseFrame(
                frame_valid=True,
                landmarks={
                    "left_shoulder": ExtractedPoseLandmark(x=0.10, y=0.20, visibility=0.95),
                    "right_shoulder": ExtractedPoseLandmark(x=0.90, y=0.20, visibility=0.95),
                },
                diagnostic_flags=[],
            ),
            ExtractedPoseFrame(
                frame_valid=True,
                landmarks={
                    "left_shoulder": ExtractedPoseLandmark(x=0.50, y=0.60, visibility=0.96),
                    "right_shoulder": ExtractedPoseLandmark(x=0.70, y=0.30, visibility=0.96),
                },
                diagnostic_flags=[],
            ),
        ]
    )

    monkeypatch.setattr(service, "_import_cv2", lambda: _FakeCV2(capture))
    monkeypatch.setattr(service, "_build_pose_backend", lambda: pose_backend)

    result = service._extract_pose_sequence_from_video_file(
        session_id=uuid4(),
        video_path=Path("/tmp/fake.mp4"),
    )

    assert result.status == "COMPLETED"
    assert result.pose_model == "mediapipe_pose"
    assert result.preprocessing_version == "phase1_v0_1_0"
    assert result.frame_count == 2
    assert result.valid_frame_count == 2
    assert result.sequence_data[0].timestamp_ms == 0.0
    assert round(result.sequence_data[1].timestamp_ms, 3) == 33.333
    assert result.sequence_data[1].landmarks["left_shoulder"].x == 0.24
    assert result.sequence_data[1].landmarks["left_shoulder"].y == 0.34
    assert result.sequence_data[1].landmarks["right_shoulder"].x == 0.83
    assert pose_backend.closed is True
    assert capture.released is True


def test_extract_pose_sequence_handles_unreadable_video(monkeypatch) -> None:
    service = PerceptionService()
    capture = _FakeVideoCapture(frames=[], opened=False)

    monkeypatch.setattr(service, "_import_cv2", lambda: _FakeCV2(capture))

    result = service._extract_pose_sequence_from_video_file(
        session_id=uuid4(),
        video_path=Path("/tmp/unreadable.mp4"),
    )

    assert result.status == "FAILED"
    assert result.frame_count == 0
    assert result.valid_frame_count == 0
    assert result.diagnostic_flags == ["VIDEO_UNREADABLE"]


def test_extract_pose_sequence_handles_zero_valid_frames(monkeypatch) -> None:
    service = PerceptionService()
    capture = _FakeVideoCapture(frames=["frame-0", "frame-1"])
    pose_backend = _FakePoseBackend(
        frames=[
            ExtractedPoseFrame(
                frame_valid=False,
                landmarks={},
                diagnostic_flags=["POSE_NOT_DETECTED"],
            ),
            ExtractedPoseFrame(
                frame_valid=False,
                landmarks={},
                diagnostic_flags=["POSE_NOT_DETECTED"],
            ),
        ]
    )

    monkeypatch.setattr(service, "_import_cv2", lambda: _FakeCV2(capture))
    monkeypatch.setattr(service, "_build_pose_backend", lambda: pose_backend)

    result = service._extract_pose_sequence_from_video_file(
        session_id=uuid4(),
        video_path=Path("/tmp/empty.mp4"),
    )

    assert result.status == "INSUFFICIENT_DATA"
    assert result.frame_count == 2
    assert result.valid_frame_count == 0
    assert result.diagnostic_flags == ["ZERO_VALID_FRAMES"]
    assert [frame.frame_valid for frame in result.sequence_data] == [False, False]
