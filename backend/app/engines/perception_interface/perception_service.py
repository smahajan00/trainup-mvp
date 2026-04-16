from __future__ import annotations

from dataclasses import dataclass

from app.engines.perception_interface.validators import (
    build_frame_batch_acceptance,
    build_live_readiness,
    validate_upload_metadata,
)
from app.schemas.session import (
    FrameBatchAcceptanceResult,
    FrameBatchRequest,
    LiveReadinessRequest,
    LiveReadinessResponse,
    UploadValidationResult,
)


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

    def accept_frame_batch(
        self,
        payload: FrameBatchRequest,
    ) -> FrameBatchAcceptanceResult:
        return build_frame_batch_acceptance(payload)
