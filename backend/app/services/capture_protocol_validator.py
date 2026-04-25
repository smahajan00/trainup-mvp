from __future__ import annotations

from dataclasses import dataclass

from app.models.drill import Drill
from app.models.enums import CameraView
from app.schemas.session import CaptureProtocolValidationResult


@dataclass(frozen=True)
class CaptureProtocolConfig:
    required: bool
    allowed_camera_views: tuple[CameraView, ...]
    canonical_view: CameraView | None


def _parse_camera_view(raw_view: object) -> CameraView | None:
    if not isinstance(raw_view, str):
        return None

    try:
        return CameraView(raw_view)
    except ValueError:
        return None


def _dedupe_camera_views(camera_views: list[CameraView]) -> tuple[CameraView, ...]:
    deduped: list[CameraView] = []
    for camera_view in camera_views:
        if camera_view not in deduped:
            deduped.append(camera_view)
    return tuple(deduped)


def _capture_protocol_config(drill: Drill) -> CaptureProtocolConfig | None:
    reference_payload = drill.reference_payload or {}
    raw_config = reference_payload.get("capture_protocol")
    if not isinstance(raw_config, dict):
        return None

    raw_views = raw_config.get("allowed_camera_views")
    if not isinstance(raw_views, list):
        raw_single_view = raw_config.get("camera_view")
        raw_views = [raw_single_view] if isinstance(raw_single_view, str) else []

    allowed_camera_views = _dedupe_camera_views(
        [
            camera_view
            for raw_view in raw_views
            if (camera_view := _parse_camera_view(raw_view)) is not None
        ]
    )
    canonical_view = _parse_camera_view(raw_config.get("canonical_view"))
    if canonical_view is None and allowed_camera_views:
        canonical_view = allowed_camera_views[0]

    return CaptureProtocolConfig(
        required=bool(raw_config.get("required", True)),
        allowed_camera_views=allowed_camera_views,
        canonical_view=canonical_view,
    )


@dataclass(frozen=True)
class CaptureProtocolValidator:
    def validate(
        self,
        *,
        drill: Drill,
        actual_view: CameraView | None,
    ) -> CaptureProtocolValidationResult:
        config = _capture_protocol_config(drill)
        if config is None or not config.allowed_camera_views:
            return CaptureProtocolValidationResult(
                is_valid=True,
                reason_code="CAPTURE_PROTOCOL_NOT_CONFIGURED",
                message="No drill-specific capture view requirement is configured.",
                expected_view=None,
                actual_view=actual_view,
            )

        expected_view = config.canonical_view
        if not config.required:
            return CaptureProtocolValidationResult(
                is_valid=True,
                reason_code="CAPTURE_PROTOCOL_NOT_REQUIRED",
                message="Capture view validation is not required for this drill.",
                expected_view=expected_view,
                actual_view=actual_view,
            )

        if actual_view is None:
            return CaptureProtocolValidationResult(
                is_valid=False,
                reason_code="CAPTURE_VIEW_MISSING",
                message="Capture view metadata is required before this drill can be evaluated.",
                expected_view=expected_view,
                actual_view=None,
            )

        if actual_view not in config.allowed_camera_views:
            return CaptureProtocolValidationResult(
                is_valid=False,
                reason_code="CAPTURE_VIEW_MISMATCH",
                message="Capture view is incompatible with the drill requirement.",
                expected_view=expected_view,
                actual_view=actual_view,
            )

        return CaptureProtocolValidationResult(
            is_valid=True,
            reason_code="CAPTURE_PROTOCOL_VALID",
            message="Capture view matches the drill requirement.",
            expected_view=expected_view,
            actual_view=actual_view,
        )
