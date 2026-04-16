from __future__ import annotations

from pathlib import Path

from app.schemas.session import (
    FrameBatchAcceptanceResult,
    FrameBatchRequest,
    LiveReadinessRequest,
    LiveReadinessResponse,
    UploadValidationResult,
)

ALLOWED_VIDEO_CONTENT_TYPES = {
    "video/mp4": {".mp4", ".m4v"},
    "video/quicktime": {".mov", ".qt"},
    "video/webm": {".webm"},
    "video/x-matroska": {".mkv"},
}
MAX_UPLOAD_FILE_SIZE_BYTES = 100 * 1024 * 1024


def normalize_content_type(content_type: str | None) -> str | None:
    if content_type is None:
        return None
    normalized = content_type.strip().lower()
    if ";" in normalized:
        normalized = normalized.split(";", maxsplit=1)[0].strip()
    return normalized or None


def validate_upload_metadata(
    *,
    file_name: str | None,
    content_type: str | None,
    file_size_bytes: int,
) -> UploadValidationResult:
    warnings: list[str] = []
    errors: list[str] = []
    normalized_content_type = normalize_content_type(content_type)

    if not file_name or not file_name.strip():
        errors.append("Uploaded media must include a filename.")

    if normalized_content_type not in ALLOWED_VIDEO_CONTENT_TYPES:
        errors.append(
            "Uploaded media must be a supported video file (MP4, MOV, WEBM, or MKV)."
        )

    if file_size_bytes <= 0:
        errors.append("Uploaded media must contain video data.")

    if file_size_bytes > MAX_UPLOAD_FILE_SIZE_BYTES:
        errors.append("Uploaded media must be 100 MB or smaller.")

    suffix = Path(file_name or "").suffix.lower()
    if suffix:
        allowed_extensions = (
            ALLOWED_VIDEO_CONTENT_TYPES.get(normalized_content_type, set())
            if normalized_content_type
            else set()
        )
        if allowed_extensions and suffix not in allowed_extensions:
            warnings.append(
                "The file extension does not perfectly match the declared video type."
            )
    else:
        warnings.append("The uploaded file has no extension; compatibility checks are limited.")

    return UploadValidationResult(
        is_valid=not errors,
        content_type=normalized_content_type,
        file_size_bytes=file_size_bytes,
        warnings=warnings,
        errors=errors,
    )


def build_live_readiness(payload: LiveReadinessRequest) -> LiveReadinessResponse:
    warnings: list[str] = []

    if not payload.camera_permission_granted:
        warnings.append("Allow camera access before starting a live session.")
    if not payload.lighting_ready:
        warnings.append("Improve lighting so the athlete stays clearly visible.")
    if not payload.framing_ready:
        warnings.append("Keep the full movement pattern inside the camera frame.")
    if not payload.space_ready:
        warnings.append("Make sure there is enough space to perform the drill safely.")
    if not payload.client_ready:
        warnings.append("Complete the on-device readiness checks before starting.")

    return LiveReadinessResponse(
        camera_ready=payload.camera_permission_granted,
        lighting_ready=payload.lighting_ready,
        framing_ready=payload.framing_ready,
        space_ready=payload.space_ready,
        warnings=warnings,
    )


def build_frame_batch_acceptance(
    payload: FrameBatchRequest,
) -> FrameBatchAcceptanceResult:
    if not payload.client_ready:
        return FrameBatchAcceptanceResult(
            accepted=False,
            frame_count=payload.frame_count,
            message=(
                "Live frame batch scaffold rejected because the client is not marked ready."
            ),
        )

    return FrameBatchAcceptanceResult(
        accepted=True,
        frame_count=payload.frame_count,
        message=(
            "Live frame batch scaffold accepted. Real-time perception processing "
            "will be added next."
        ),
    )
