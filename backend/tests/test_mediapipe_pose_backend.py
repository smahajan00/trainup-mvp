from __future__ import annotations

import builtins
import sys
from types import ModuleType, SimpleNamespace

import pytest

from app.engines.perception_interface.mediapipe_pose_backend import (
    MediaPipePoseBackend,
    MediaPipeUnavailableError,
)


class _FakePoseRuntime:
    PoseLandmark = [
        SimpleNamespace(name="NOSE"),
        SimpleNamespace(name="LEFT_SHOULDER"),
        SimpleNamespace(name="RIGHT_SHOULDER"),
    ]

    class Pose:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def process(self, frame_rgb):
            del frame_rgb
            return SimpleNamespace(
                pose_landmarks=SimpleNamespace(
                    landmark=[
                        SimpleNamespace(x=0.1, y=0.2, visibility=0.9),
                        SimpleNamespace(x=0.2, y=0.3, visibility=0.8),
                        SimpleNamespace(x=0.3, y=0.4, visibility=0.7),
                    ]
                )
            )

        def close(self) -> None:
            return None


def test_backend_initializes_with_legacy_solutions(monkeypatch) -> None:
    fake_cv2 = ModuleType("cv2")
    fake_mp = ModuleType("mediapipe")
    fake_mp.solutions = SimpleNamespace(pose=_FakePoseRuntime)

    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)
    monkeypatch.setitem(sys.modules, "mediapipe", fake_mp)

    backend = MediaPipePoseBackend()
    result = backend.extract(frame_rgb="frame")

    assert result.frame_valid is True
    assert sorted(result.landmarks.keys()) == [
        "left_shoulder",
        "nose",
        "right_shoulder",
    ]


def test_backend_rejects_tasks_only_mediapipe(monkeypatch) -> None:
    fake_mp = ModuleType("mediapipe")
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "mediapipe.python.solutions":
            raise ModuleNotFoundError(name)
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(MediaPipeUnavailableError) as excinfo:
        MediaPipePoseBackend._resolve_pose_module(fake_mp)

    assert "legacy Pose solutions API" in str(excinfo.value)
