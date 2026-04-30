from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class MediaPipeUnavailableError(RuntimeError):
    """Raised when MediaPipe dependencies are not installed."""


@dataclass(frozen=True)
class ExtractedPoseLandmark:
    x: float
    y: float
    visibility: float


@dataclass(frozen=True)
class ExtractedPoseFrame:
    frame_valid: bool
    landmarks: dict[str, ExtractedPoseLandmark]
    diagnostic_flags: list[str]


class MediaPipePoseBackend:
    def __init__(self) -> None:
        try:
            import cv2  # noqa: F401
            import mediapipe as mp
        except (ModuleNotFoundError, ImportError) as exc:
            raise MediaPipeUnavailableError(
                f"MediaPipe Pose dependencies are unavailable: {exc}"
            ) from exc

        pose_module = self._resolve_pose_module(mp)
        self._mp_pose = pose_module
        try:
            self._pose = self._mp_pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                smooth_landmarks=False,
                enable_segmentation=False,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
        except Exception as exc:  # pragma: no cover - runtime backend guard
            raise MediaPipeUnavailableError(
                f"MediaPipe Pose initialization failed: {exc}"
            ) from exc
        self._landmark_names = [
            landmark.name.lower() for landmark in self._mp_pose.PoseLandmark
        ]

    def extract(self, *, frame_rgb: Any) -> ExtractedPoseFrame:
        results = self._pose.process(frame_rgb)
        if results.pose_landmarks is None:
            return ExtractedPoseFrame(
                frame_valid=False,
                landmarks={},
                diagnostic_flags=["POSE_NOT_DETECTED"],
            )

        landmarks = {
            landmark_name: ExtractedPoseLandmark(
                x=float(landmark.x),
                y=float(landmark.y),
                visibility=float(landmark.visibility),
            )
            for landmark_name, landmark in zip(
                self._landmark_names,
                results.pose_landmarks.landmark,
                strict=False,
            )
        }
        return ExtractedPoseFrame(
            frame_valid=True,
            landmarks=landmarks,
            diagnostic_flags=[],
        )

    def close(self) -> None:
        self._pose.close()

    @staticmethod
    def _resolve_pose_module(mp: Any) -> Any:
        solutions = getattr(mp, "solutions", None)
        if solutions is not None and hasattr(solutions, "pose"):
            return solutions.pose

        try:
            from mediapipe.python.solutions import pose as legacy_pose
        except ModuleNotFoundError as exc:
            raise MediaPipeUnavailableError(
                "Installed mediapipe package does not expose the legacy Pose "
                "solutions API required by TrainUp Phase 1. Pin mediapipe==0.10.14."
            ) from exc

        return legacy_pose
