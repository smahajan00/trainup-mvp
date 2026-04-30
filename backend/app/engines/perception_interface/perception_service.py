from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Iterator
from uuid import UUID

from app.engines.perception_interface.mediapipe_pose_backend import (
    ExtractedPoseFrame,
    ExtractedPoseLandmark,
    MediaPipePoseBackend,
    MediaPipeUnavailableError,
)
from app.engines.perception_interface.validators import (
    build_frame_batch_acceptance,
    build_live_readiness,
    normalize_content_type,
    validate_upload_metadata,
)
from app.schemas.session import (
    FrameBatchAcceptanceResult,
    FrameBatchRequest,
    LiveReadinessRequest,
    LiveReadinessResponse,
    PoseFrameResponse,
    PoseLandmarkCoordinate,
    PoseSequenceResponse,
    UploadValidationResult,
)

VISIBILITY_THRESHOLD = 0.50
EMA_ALPHA = 0.35
POSE_MODEL_NAME = "mediapipe_pose"
PREPROCESSING_VERSION = "phase1_v0_1_0"
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DecodedVideoFrame:
    frame_index: int
    timestamp_ms: float
    frame_bgr: Any


@dataclass
class PerceptionService:
    def validate_upload(
        self,
        *,
        file_name: str | None,
        content_type: str | None,
        file_size_bytes: int,
    ) -> UploadValidationResult:
        return validate_upload_metadata(
            file_name=file_name,
            content_type=content_type,
            file_size_bytes=file_size_bytes,
        )

    def validate_live_readiness(
        self,
        payload: LiveReadinessRequest,
    ) -> LiveReadinessResponse:
        return build_live_readiness(payload)

    def process_uploaded_file(
        self,
        *,
        session_id: UUID,
        drill_id: UUID,
        file_name: str,
        content_type: str,
        file_size_bytes: int,
        tracked_joints: list[str],
        file_bytes: bytes,
    ) -> PoseSequenceResponse:
        del drill_id
        del file_size_bytes
        del tracked_joints

        try:
            with self._temporary_video_file(
                file_name=file_name,
                content_type=content_type,
                file_bytes=file_bytes,
            ) as video_path:
                return self._extract_pose_sequence_from_video_file(
                    session_id=session_id,
                    video_path=video_path,
                )
        except MediaPipeUnavailableError as exc:
            logger.exception(
                "Pose extraction runtime unavailable",
                extra={
                    "session_id": str(session_id),
                    "file_name": file_name,
                    "content_type": content_type,
                },
            )
            return self._build_pose_sequence(
                session_id=session_id,
                frames=[],
                status="FAILED",
                diagnostic_flags=self._build_failure_diagnostic_flags(
                    exc,
                    runtime_unavailable=True,
                ),
            )
        except Exception as exc:
            logger.exception(
                "Pose extraction failed",
                extra={
                    "session_id": str(session_id),
                    "file_name": file_name,
                    "content_type": content_type,
                },
            )
            return self._build_pose_sequence(
                session_id=session_id,
                frames=[],
                status="FAILED",
                diagnostic_flags=self._build_failure_diagnostic_flags(exc),
            )

    def accept_frame_batch(
        self,
        payload: FrameBatchRequest,
    ) -> FrameBatchAcceptanceResult:
        return build_frame_batch_acceptance(payload)

    @contextmanager
    def _temporary_video_file(
        self,
        *,
        file_name: str,
        content_type: str,
        file_bytes: bytes,
    ) -> Iterator[Path]:
        suffix = Path(file_name).suffix or self._suffix_for_content_type(content_type)
        temp_file = NamedTemporaryFile(delete=False, suffix=suffix)
        temp_path = Path(temp_file.name)

        try:
            temp_file.write(file_bytes)
            temp_file.flush()
            temp_file.close()
            yield temp_path
        finally:
            # Raw video bytes are discarded immediately after decoding completes.
            if temp_path.exists():
                temp_path.unlink()

    def _extract_pose_sequence_from_video_file(
        self,
        *,
        session_id: UUID,
        video_path: Path,
    ) -> PoseSequenceResponse:
        cv2 = self._import_cv2()
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            return self._build_pose_sequence(
                session_id=session_id,
                frames=[],
                status="FAILED",
                diagnostic_flags=["VIDEO_UNREADABLE"],
            )

        pose_backend = self._build_pose_backend()
        raw_frames: list[PoseFrameResponse] = []

        try:
            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
            while True:
                success, frame_bgr = capture.read()
                if not success:
                    break

                frame_index = len(raw_frames)
                timestamp_ms = float(capture.get(cv2.CAP_PROP_POS_MSEC) or 0.0)
                if timestamp_ms <= 0 and fps > 0:
                    timestamp_ms = (frame_index / fps) * 1000

                raw_frame = self._extract_pose_frame(
                    session_id=session_id,
                    decoded_frame=DecodedVideoFrame(
                        frame_index=frame_index,
                        timestamp_ms=round(timestamp_ms, 3),
                        frame_bgr=frame_bgr,
                    ),
                    pose_backend=pose_backend,
                )
                raw_frames.append(raw_frame)

                # Drop the raw frame immediately after landmarks are extracted.
                del frame_bgr
        finally:
            capture.release()
            pose_backend.close()

        if not raw_frames:
            return self._build_pose_sequence(
                session_id=session_id,
                frames=[],
                status="INSUFFICIENT_DATA",
                diagnostic_flags=["ZERO_FRAMES"],
            )

        processed_frames = self._apply_preprocessing(raw_frames)
        valid_frame_count = sum(1 for frame in processed_frames if frame.frame_valid)
        status = "COMPLETED" if valid_frame_count > 0 else "INSUFFICIENT_DATA"
        diagnostic_flags: list[str] = []
        if valid_frame_count == 0:
            diagnostic_flags.append("ZERO_VALID_FRAMES")

        return self._build_pose_sequence(
            session_id=session_id,
            frames=processed_frames,
            status=status,
            diagnostic_flags=diagnostic_flags,
        )

    def _extract_pose_frame(
        self,
        *,
        session_id: UUID,
        decoded_frame: DecodedVideoFrame,
        pose_backend: MediaPipePoseBackend,
    ) -> PoseFrameResponse:
        cv2 = self._import_cv2()
        try:
            frame_rgb = cv2.cvtColor(decoded_frame.frame_bgr, cv2.COLOR_BGR2RGB)
            extracted_frame = pose_backend.extract(frame_rgb=frame_rgb)
        except Exception:
            extracted_frame = ExtractedPoseFrame(
                frame_valid=False,
                landmarks={},
                diagnostic_flags=["POSE_EXTRACTION_ERROR"],
            )
        return PoseFrameResponse(
            session_id=session_id,
            frame_index=decoded_frame.frame_index,
            timestamp_ms=decoded_frame.timestamp_ms,
            landmarks={
                name: PoseLandmarkCoordinate(
                    x=landmark.x,
                    y=landmark.y,
                    visibility=landmark.visibility,
                )
                for name, landmark in extracted_frame.landmarks.items()
            },
            frame_valid=extracted_frame.frame_valid,
            diagnostic_flags=list(extracted_frame.diagnostic_flags),
        )

    def _apply_preprocessing(
        self,
        frames: list[PoseFrameResponse],
    ) -> list[PoseFrameResponse]:
        smoothed_landmarks_by_name: dict[str, ExtractedPoseLandmark] = {}
        processed_frames: list[PoseFrameResponse] = []

        for frame in frames:
            processed_landmarks: dict[str, PoseLandmarkCoordinate] = {}
            frame_flags = list(frame.diagnostic_flags)

            for landmark_name, landmark in frame.landmarks.items():
                if landmark.visibility < VISIBILITY_THRESHOLD:
                    frame_flags.append(f"LOW_VISIBILITY:{landmark_name}")
                    processed_landmarks[landmark_name] = landmark
                    continue

                previous = smoothed_landmarks_by_name.get(landmark_name)
                if previous is None:
                    smoothed = ExtractedPoseLandmark(
                        x=landmark.x,
                        y=landmark.y,
                        visibility=landmark.visibility,
                    )
                else:
                    smoothed = ExtractedPoseLandmark(
                        x=(EMA_ALPHA * landmark.x) + ((1 - EMA_ALPHA) * previous.x),
                        y=(EMA_ALPHA * landmark.y) + ((1 - EMA_ALPHA) * previous.y),
                        visibility=landmark.visibility,
                    )

                smoothed_landmarks_by_name[landmark_name] = smoothed
                processed_landmarks[landmark_name] = PoseLandmarkCoordinate(
                    x=round(smoothed.x, 6),
                    y=round(smoothed.y, 6),
                    visibility=round(smoothed.visibility, 6),
                )

            processed_frames.append(
                PoseFrameResponse(
                    session_id=frame.session_id,
                    frame_index=frame.frame_index,
                    timestamp_ms=frame.timestamp_ms,
                    landmarks=processed_landmarks,
                    frame_valid=frame.frame_valid,
                    diagnostic_flags=frame_flags,
                )
            )

        return processed_frames

    @staticmethod
    def _build_pose_sequence(
        *,
        session_id: UUID,
        frames: list[PoseFrameResponse],
        status: str,
        diagnostic_flags: list[str],
    ) -> PoseSequenceResponse:
        return PoseSequenceResponse(
            session_id=session_id,
            pose_model=POSE_MODEL_NAME,
            preprocessing_version=PREPROCESSING_VERSION,
            frame_count=len(frames),
            valid_frame_count=sum(1 for frame in frames if frame.frame_valid),
            status=status,
            diagnostic_flags=diagnostic_flags,
            sequence_data=frames,
            created_at=None,
        )

    @staticmethod
    def _suffix_for_content_type(content_type: str | None) -> str:
        normalized = normalize_content_type(content_type)
        suffixes = {
            "video/mp4": ".mp4",
            "video/quicktime": ".mov",
            "video/webm": ".webm",
            "video/x-matroska": ".mkv",
        }
        return suffixes.get(normalized, ".mp4")

    @staticmethod
    def _import_cv2() -> Any:
        try:
            import cv2
        except (ModuleNotFoundError, ImportError) as exc:
            raise MediaPipeUnavailableError(
                f"OpenCV runtime dependencies are unavailable: {exc}"
            ) from exc
        return cv2

    @staticmethod
    def _build_pose_backend() -> MediaPipePoseBackend:
        return MediaPipePoseBackend()

    @staticmethod
    def _build_failure_diagnostic_flags(
        exc: Exception,
        *,
        runtime_unavailable: bool = False,
    ) -> list[str]:
        message = str(exc)
        upper_message = message.upper()
        diagnostic_flags = ["POSE_EXTRACTION_FAILURE"]

        if runtime_unavailable:
            diagnostic_flags.append("PERCEPTION_RUNTIME_UNAVAILABLE")

        if "OPENCV" in upper_message:
            diagnostic_flags.append("OPENCV_RUNTIME_UNAVAILABLE")

        if "MEDIAPIPE" in upper_message or "POSE" in upper_message:
            diagnostic_flags.append("MEDIAPIPE_RUNTIME_UNAVAILABLE")

        for library_name in ("LIBXCB.SO.1", "LIBGL.SO.1", "LIBGTHREAD-2.0.SO.0"):
            if library_name in upper_message:
                diagnostic_flags.append(
                    f"MISSING_SYSTEM_LIBRARY:{library_name.replace('.', '_')}"
                )

        diagnostic_flags.append(
            f"POSE_EXTRACTION_EXCEPTION:{exc.__class__.__name__.upper()}"
        )
        return diagnostic_flags
