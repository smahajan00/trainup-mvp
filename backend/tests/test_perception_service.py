from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.engines.perception_interface.mediapipe_pose_backend import (
    ExtractedPoseFrame,
    ExtractedPoseLandmark,
    MediaPipeUnavailableError,
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
        if prop == 4:
            return len(self._frames)
        return 0.0

    def release(self) -> None:
        self.released = True


class _FakeCV2:
    CAP_PROP_FPS = 1
    CAP_PROP_POS_MSEC = 2
    CAP_PROP_FRAME_COUNT = 4
    COLOR_BGR2RGB = 3
    INTER_AREA = 5

    def __init__(self, capture: _FakeVideoCapture) -> None:
        self._capture = capture
        self.resize_calls: list[tuple[object, tuple[int, int], int]] = []

    def VideoCapture(self, _: str) -> _FakeVideoCapture:
        return self._capture

    def cvtColor(self, frame_bgr: object, _: int) -> object:
        return frame_bgr

    def resize(
        self,
        frame_bgr: object,
        size: tuple[int, int],
        *,
        interpolation: int,
    ) -> object:
        self.resize_calls.append((frame_bgr, size, interpolation))
        return _FakeFrame(width=size[0], height=size[1])


class _FakeFrame:
    def __init__(self, *, width: int, height: int) -> None:
        self.shape = (height, width, 3)


class _FakePoseBackend:
    def __init__(self, frames: list[ExtractedPoseFrame]) -> None:
        self._frames = list(frames)
        self._position = 0
        self.seen_frames: list[object] = []
        self.closed = False

    def extract(self, *, frame_rgb: object) -> ExtractedPoseFrame:
        self.seen_frames.append(frame_rgb)
        frame = self._frames[self._position]
        self._position += 1
        return frame

    def close(self) -> None:
        self.closed = True


def test_extract_pose_sequence_success_applies_ema_smoothing(monkeypatch) -> None:
    service = PerceptionService()
    capture = _FakeVideoCapture(frames=["frame-0", "frame-1"], fps=12.0)
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
    assert round(result.sequence_data[1].timestamp_ms, 3) == 83.333
    assert result.sequence_data[1].landmarks["left_shoulder"].x == 0.24
    assert result.sequence_data[1].landmarks["left_shoulder"].y == 0.34
    assert result.sequence_data[1].landmarks["right_shoulder"].x == 0.83
    assert pose_backend.closed is True
    assert capture.released is True
    assert result.processing_metadata is not None
    assert result.processing_metadata.original_frame_count == 2
    assert result.processing_metadata.processed_frame_count == 2
    assert result.processing_metadata.target_pose_fps == 12.0
    assert result.processing_metadata.sampling_stride == 1


def test_extract_pose_sequence_downsamples_high_fps_video(monkeypatch) -> None:
    service = PerceptionService()
    capture = _FakeVideoCapture(
        frames=[f"frame-{index}" for index in range(10)],
        fps=30.0,
    )
    pose_backend = _FakePoseBackend(
        frames=[
            ExtractedPoseFrame(
                frame_valid=True,
                landmarks={
                    "left_shoulder": ExtractedPoseLandmark(
                        x=0.10,
                        y=0.20,
                        visibility=0.95,
                    ),
                },
                diagnostic_flags=[],
            )
            for _ in range(4)
        ]
    )

    monkeypatch.setattr(service, "_import_cv2", lambda: _FakeCV2(capture))
    monkeypatch.setattr(service, "_build_pose_backend", lambda: pose_backend)

    result = service._extract_pose_sequence_from_video_file(
        session_id=uuid4(),
        video_path=Path("/tmp/high-fps.mp4"),
    )

    assert result.status == "COMPLETED"
    assert result.frame_count == 4
    assert result.valid_frame_count == 4
    assert [frame.frame_index for frame in result.sequence_data] == [0, 3, 6, 9]
    assert [frame.timestamp_ms for frame in result.sequence_data] == [
        0.0,
        100.0,
        200.0,
        300.0,
    ]
    assert result.processing_metadata is not None
    assert result.processing_metadata.original_fps == 30.0
    assert result.processing_metadata.target_pose_fps == 12.0
    assert result.processing_metadata.sampling_stride == 3
    assert result.processing_metadata.original_frame_count == 10
    assert result.processing_metadata.processed_frame_count == 4


def test_extract_pose_sequence_resizes_large_frames_before_inference(monkeypatch) -> None:
    service = PerceptionService()
    capture = _FakeVideoCapture(frames=[_FakeFrame(width=1920, height=1080)], fps=12.0)
    fake_cv2 = _FakeCV2(capture)
    pose_backend = _FakePoseBackend(
        frames=[
            ExtractedPoseFrame(
                frame_valid=True,
                landmarks={
                    "left_shoulder": ExtractedPoseLandmark(
                        x=0.10,
                        y=0.20,
                        visibility=0.95,
                    ),
                },
                diagnostic_flags=[],
            )
        ]
    )

    monkeypatch.setattr(service, "_import_cv2", lambda: fake_cv2)
    monkeypatch.setattr(service, "_build_pose_backend", lambda: pose_backend)

    result = service._extract_pose_sequence_from_video_file(
        session_id=uuid4(),
        video_path=Path("/tmp/large.mp4"),
    )

    assert result.status == "COMPLETED"
    assert fake_cv2.resize_calls[0][1] == (720, 405)
    assert pose_backend.seen_frames[0].shape == (405, 720, 3)
    assert result.sequence_data[0].landmarks["left_shoulder"].x == 0.1
    assert result.sequence_data[0].landmarks["left_shoulder"].y == 0.2
    assert result.processing_metadata is not None
    assert result.processing_metadata.original_width == 1920
    assert result.processing_metadata.original_height == 1080
    assert result.processing_metadata.inference_width == 720
    assert result.processing_metadata.inference_height == 405


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
    capture = _FakeVideoCapture(frames=["frame-0", "frame-1"], fps=12.0)
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


def test_process_uploaded_file_surfaces_runtime_dependency_details(monkeypatch) -> None:
    service = PerceptionService()

    monkeypatch.setattr(
        service,
        "_temporary_video_file",
        lambda **_: __import__("contextlib").nullcontext(Path("/tmp/fake.mov")),
    )
    monkeypatch.setattr(
        service,
        "_extract_pose_sequence_from_video_file",
        lambda **_: (_ for _ in ()).throw(
            MediaPipeUnavailableError(
                "OpenCV runtime dependencies are unavailable: libxcb.so.1 missing"
            )
        ),
    )

    result = service.process_uploaded_file(
        session_id=uuid4(),
        drill_id=uuid4(),
        file_name="test.mov",
        content_type="video/quicktime",
        file_size_bytes=1024,
        tracked_joints=[],
        file_bytes=b"test",
    )

    assert result.status == "FAILED"
    assert result.frame_count == 0
    assert result.valid_frame_count == 0
    assert "POSE_EXTRACTION_FAILURE" in result.diagnostic_flags
    assert "PERCEPTION_RUNTIME_UNAVAILABLE" in result.diagnostic_flags
    assert "OPENCV_RUNTIME_UNAVAILABLE" in result.diagnostic_flags
    assert "MISSING_SYSTEM_LIBRARY:LIBXCB_SO_1" in result.diagnostic_flags
