from __future__ import annotations

import logging
import math
import time
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
from app.core.config import get_settings
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
    PoseProcessingCacheKey,
    PoseProcessingMetadata,
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


@dataclass(frozen=True)
class PoseExtractionSettings:
    target_pose_fps: float
    max_inference_width: int


@dataclass(frozen=True)
class FrameResizeResult:
    frame_bgr: Any
    original_width: int | None
    original_height: int | None
    inference_width: int | None
    inference_height: int | None


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
        cache_key: PoseProcessingCacheKey | None = None,
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
                    cache_key=cache_key,
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
                metadata=self._build_empty_processing_metadata(cache_key=cache_key),
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
                metadata=self._build_empty_processing_metadata(cache_key=cache_key),
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
        cache_key: PoseProcessingCacheKey | None = None,
    ) -> PoseSequenceResponse:
        started_at = time.perf_counter()
        cv2 = self._import_cv2()
        settings = self._get_pose_extraction_settings()
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            return self._build_pose_sequence(
                session_id=session_id,
                frames=[],
                status="FAILED",
                diagnostic_flags=["VIDEO_UNREADABLE"],
                metadata=self._build_empty_processing_metadata(
                    cache_key=cache_key,
                    target_pose_fps=settings.target_pose_fps,
                    max_inference_width=settings.max_inference_width,
                    processing_time_ms=self._elapsed_ms(started_at),
                ),
            )

        pose_backend = self._build_pose_backend()
        raw_frames: list[PoseFrameResponse] = []
        original_frame_count = 0
        first_original_width: int | None = None
        first_original_height: int | None = None
        first_inference_width: int | None = None
        first_inference_height: int | None = None

        try:
            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
            sampling_stride = self._build_sampling_stride(
                original_fps=fps,
                target_pose_fps=settings.target_pose_fps,
            )
            reported_frame_count = self._read_capture_count(cv2=cv2, capture=capture)
            while True:
                success, frame_bgr = capture.read()
                if not success:
                    break

                frame_index = original_frame_count
                original_frame_count += 1

                if frame_index % sampling_stride != 0:
                    del frame_bgr
                    continue

                timestamp_ms = float(capture.get(cv2.CAP_PROP_POS_MSEC) or 0.0)
                if timestamp_ms <= 0 and fps > 0:
                    timestamp_ms = (frame_index / fps) * 1000

                resized_frame = self._resize_frame_for_inference(
                    cv2=cv2,
                    frame_bgr=frame_bgr,
                    max_width=settings.max_inference_width,
                )
                first_original_width = first_original_width or resized_frame.original_width
                first_original_height = first_original_height or resized_frame.original_height
                first_inference_width = first_inference_width or resized_frame.inference_width
                first_inference_height = first_inference_height or resized_frame.inference_height

                raw_frame = self._extract_pose_frame(
                    session_id=session_id,
                    decoded_frame=DecodedVideoFrame(
                        frame_index=frame_index,
                        timestamp_ms=round(timestamp_ms, 3),
                        frame_bgr=resized_frame.frame_bgr,
                    ),
                    pose_backend=pose_backend,
                )
                raw_frames.append(raw_frame)

                # Drop the raw frame immediately after landmarks are extracted.
                del frame_bgr
                del resized_frame
        finally:
            capture.release()
            pose_backend.close()

        original_frame_count = max(original_frame_count, reported_frame_count)
        metadata = self._build_processing_metadata(
            original_fps=fps,
            target_pose_fps=settings.target_pose_fps,
            sampling_stride=sampling_stride,
            original_frame_count=original_frame_count,
            processed_frame_count=len(raw_frames),
            valid_frame_count=sum(1 for frame in raw_frames if frame.frame_valid),
            original_width=first_original_width,
            original_height=first_original_height,
            inference_width=first_inference_width,
            inference_height=first_inference_height,
            cache_key=cache_key,
            cache_hit=False,
            processing_time_ms=self._elapsed_ms(started_at),
        )

        if not raw_frames:
            return self._build_pose_sequence(
                session_id=session_id,
                frames=[],
                status="INSUFFICIENT_DATA",
                diagnostic_flags=["ZERO_FRAMES"],
                metadata=metadata,
            )

        processed_frames = self._apply_preprocessing(raw_frames)
        valid_frame_count = sum(1 for frame in processed_frames if frame.frame_valid)
        metadata = metadata.model_copy(update={"valid_frame_count": valid_frame_count})
        status = "COMPLETED" if valid_frame_count > 0 else "INSUFFICIENT_DATA"
        diagnostic_flags: list[str] = []
        if valid_frame_count == 0:
            diagnostic_flags.append("ZERO_VALID_FRAMES")

        return self._build_pose_sequence(
            session_id=session_id,
            frames=processed_frames,
            status=status,
            diagnostic_flags=diagnostic_flags,
            metadata=metadata,
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
        metadata: PoseProcessingMetadata | None = None,
    ) -> PoseSequenceResponse:
        return PoseSequenceResponse(
            session_id=session_id,
            pose_model=POSE_MODEL_NAME,
            preprocessing_version=PREPROCESSING_VERSION,
            frame_count=len(frames),
            valid_frame_count=sum(1 for frame in frames if frame.frame_valid),
            status=status,
            diagnostic_flags=diagnostic_flags,
            processing_metadata=metadata,
            sequence_data=frames,
            created_at=None,
        )

    @staticmethod
    def _get_pose_extraction_settings() -> PoseExtractionSettings:
        settings = get_settings()
        return PoseExtractionSettings(
            target_pose_fps=max(float(settings.pose_target_fps), 1.0),
            max_inference_width=max(int(settings.pose_max_width), 1),
        )

    @staticmethod
    def _build_sampling_stride(
        *,
        original_fps: float,
        target_pose_fps: float,
    ) -> int:
        if original_fps <= 0 or original_fps <= target_pose_fps:
            return 1
        return max(1, math.ceil(original_fps / target_pose_fps))

    @staticmethod
    def _read_capture_count(*, cv2: Any, capture: Any) -> int:
        frame_count_prop = getattr(cv2, "CAP_PROP_FRAME_COUNT", None)
        if frame_count_prop is None:
            return 0
        return int(capture.get(frame_count_prop) or 0)

    @staticmethod
    def _resize_frame_for_inference(
        *,
        cv2: Any,
        frame_bgr: Any,
        max_width: int,
    ) -> FrameResizeResult:
        shape = getattr(frame_bgr, "shape", None)
        if not shape or len(shape) < 2:
            return FrameResizeResult(
                frame_bgr=frame_bgr,
                original_width=None,
                original_height=None,
                inference_width=None,
                inference_height=None,
            )

        original_height = int(shape[0])
        original_width = int(shape[1])
        if original_width <= 0 or original_height <= 0 or original_width <= max_width:
            return FrameResizeResult(
                frame_bgr=frame_bgr,
                original_width=original_width,
                original_height=original_height,
                inference_width=original_width,
                inference_height=original_height,
            )

        scale = max_width / original_width
        inference_width = max_width
        inference_height = max(1, int(round(original_height * scale)))
        resized_frame = cv2.resize(
            frame_bgr,
            (inference_width, inference_height),
            interpolation=getattr(cv2, "INTER_AREA", 3),
        )
        return FrameResizeResult(
            frame_bgr=resized_frame,
            original_width=original_width,
            original_height=original_height,
            inference_width=inference_width,
            inference_height=inference_height,
        )

    @staticmethod
    def _build_processing_metadata(
        *,
        original_fps: float | None,
        target_pose_fps: float,
        sampling_stride: int,
        original_frame_count: int,
        processed_frame_count: int,
        valid_frame_count: int,
        original_width: int | None,
        original_height: int | None,
        inference_width: int | None,
        inference_height: int | None,
        cache_key: PoseProcessingCacheKey | None,
        cache_hit: bool,
        processing_time_ms: float | None,
    ) -> PoseProcessingMetadata:
        return PoseProcessingMetadata(
            original_fps=round(original_fps, 3) if original_fps else None,
            target_pose_fps=target_pose_fps,
            sampling_stride=sampling_stride,
            original_frame_count=original_frame_count,
            processed_frame_count=processed_frame_count,
            valid_frame_count=valid_frame_count,
            original_width=original_width,
            original_height=original_height,
            inference_width=inference_width,
            inference_height=inference_height,
            cache_key=cache_key,
            cache_hit=cache_hit,
            processing_time_ms=processing_time_ms,
        )

    def _build_empty_processing_metadata(
        self,
        *,
        cache_key: PoseProcessingCacheKey | None,
        target_pose_fps: float | None = None,
        max_inference_width: int | None = None,
        processing_time_ms: float | None = None,
    ) -> PoseProcessingMetadata:
        settings = self._get_pose_extraction_settings()
        del max_inference_width
        return self._build_processing_metadata(
            original_fps=None,
            target_pose_fps=target_pose_fps or settings.target_pose_fps,
            sampling_stride=1,
            original_frame_count=0,
            processed_frame_count=0,
            valid_frame_count=0,
            original_width=None,
            original_height=None,
            inference_width=None,
            inference_height=None,
            cache_key=cache_key,
            cache_hit=False,
            processing_time_ms=processing_time_ms,
        )

    @staticmethod
    def _elapsed_ms(started_at: float) -> float:
        return round((time.perf_counter() - started_at) * 1000, 3)

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
