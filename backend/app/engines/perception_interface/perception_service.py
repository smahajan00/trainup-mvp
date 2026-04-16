from __future__ import annotations

import hashlib
from dataclasses import dataclass
from math import sin
from uuid import UUID

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
    PerceptionDerivedMotionFeatures,
    PerceptionFileMetadata,
    PerceptionFramePayload,
    PerceptionKeypointCoordinate,
    PerceptionProcessingSummary,
    PerceptionResult,
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
    ) -> PerceptionResult:
        seed = self._derive_seed(
            session_id=session_id,
            drill_id=drill_id,
            file_name=file_name,
            file_size_bytes=file_size_bytes,
            file_bytes=file_bytes,
        )
        frame_count = min(180, 48 + (file_size_bytes // 250_000) + (seed % 36))
        fps_estimate = float(24 + (seed % 7))
        duration_seconds = round(frame_count / fps_estimate, 3)
        keypoint_series = self._build_keypoint_series(
            seed=seed,
            tracked_joints=tracked_joints,
            fps_estimate=fps_estimate,
            sample_count=min(frame_count, 12),
        )
        available_joint_count = len(keypoint_series[0].keypoints) if keypoint_series else 0
        average_confidence = (
            sum(frame.confidence for frame in keypoint_series) / len(keypoint_series)
            if keypoint_series
            else 0.0
        )
        missing_frame_ratio = round(((seed % 5) + 1) / 100, 3)
        stability_hint = round(
            max(
                0.0,
                min(
                    (average_confidence * 0.72)
                    + (min(available_joint_count / 12, 1.0) * 0.12)
                    + ((1 - missing_frame_ratio) * 0.16),
                    1.0,
                ),
            ),
            3,
        )

        return PerceptionResult(
            source_type="upload",
            file_metadata=PerceptionFileMetadata(
                file_name=file_name,
                content_type=content_type,
                file_size_bytes=file_size_bytes,
            ),
            processing_summary=PerceptionProcessingSummary(
                frame_count=frame_count,
                duration_seconds=duration_seconds,
                fps_estimate=fps_estimate,
                processing_mode="scaffold",
            ),
            keypoint_series=keypoint_series,
            derived_motion_features=PerceptionDerivedMotionFeatures(
                available_joint_count=available_joint_count,
                missing_frame_ratio=missing_frame_ratio,
                stability_hint=stability_hint,
            ),
        )

    def accept_frame_batch(
        self,
        payload: FrameBatchRequest,
    ) -> FrameBatchAcceptanceResult:
        return build_frame_batch_acceptance(payload)

    @staticmethod
    def _derive_seed(
        *,
        session_id: UUID,
        drill_id: UUID,
        file_name: str,
        file_size_bytes: int,
        file_bytes: bytes,
    ) -> int:
        digest = hashlib.sha256()
        digest.update(str(session_id).encode("utf-8"))
        digest.update(str(drill_id).encode("utf-8"))
        digest.update(file_name.encode("utf-8"))
        digest.update(str(file_size_bytes).encode("utf-8"))
        digest.update(file_bytes[:8192])
        return int(digest.hexdigest()[:8], 16)

    def _build_keypoint_series(
        self,
        *,
        seed: int,
        tracked_joints: list[str],
        fps_estimate: float,
        sample_count: int,
    ) -> list[PerceptionFramePayload]:
        labels = self._expand_joint_labels(tracked_joints)
        frames: list[PerceptionFramePayload] = []

        for frame_index in range(sample_count):
            keypoints: dict[str, PerceptionKeypointCoordinate] = {}
            timestamp = round(frame_index / fps_estimate, 3)
            confidence = round(0.74 + (((seed + frame_index * 13) % 18) / 100), 3)

            for keypoint_index, label in enumerate(labels):
                x, y, z = self._coordinate_for_label(
                    label=label,
                    seed=seed,
                    frame_index=frame_index,
                    keypoint_index=keypoint_index,
                )
                keypoints[label] = PerceptionKeypointCoordinate(x=x, y=y, z=z)

            frames.append(
                PerceptionFramePayload(
                    frame_index=frame_index,
                    timestamp=timestamp,
                    confidence=confidence,
                    keypoints=keypoints,
                )
            )

        return frames

    @staticmethod
    def _expand_joint_labels(tracked_joints: list[str]) -> list[str]:
        label_map = {
            "shoulders": ["left_shoulder", "right_shoulder"],
            "elbows": ["left_elbow", "right_elbow"],
            "wrists": ["left_wrist", "right_wrist"],
            "hips": ["left_hip", "right_hip"],
            "knees": ["left_knee", "right_knee"],
            "ankles": ["left_ankle", "right_ankle"],
            "torso": ["pelvis_center", "sternum_center"],
        }
        labels: list[str] = []
        for joint in tracked_joints:
            labels.extend(label_map.get(joint, [joint]))
        return labels or ["pelvis_center", "sternum_center"]

    @staticmethod
    def _coordinate_for_label(
        *,
        label: str,
        seed: int,
        frame_index: int,
        keypoint_index: int,
    ) -> tuple[float, float, float]:
        base_positions: dict[str, tuple[float, float, float]] = {
            "left_shoulder": (0.42, 0.18, -0.02),
            "right_shoulder": (0.58, 0.18, 0.02),
            "left_elbow": (0.39, 0.29, -0.03),
            "right_elbow": (0.61, 0.29, 0.03),
            "left_wrist": (0.37, 0.4, -0.05),
            "right_wrist": (0.63, 0.4, 0.05),
            "left_hip": (0.45, 0.46, -0.02),
            "right_hip": (0.55, 0.46, 0.02),
            "left_knee": (0.46, 0.68, -0.01),
            "right_knee": (0.54, 0.68, 0.01),
            "left_ankle": (0.47, 0.88, 0.0),
            "right_ankle": (0.53, 0.88, 0.0),
            "pelvis_center": (0.5, 0.48, 0.0),
            "sternum_center": (0.5, 0.28, 0.0),
        }
        base_x, base_y, base_z = base_positions.get(label, (0.5, 0.5, 0.0))
        oscillation = sin((seed % 17 + frame_index + keypoint_index) * 0.35)
        x = round(base_x + (oscillation * 0.012), 3)
        y = round(base_y + (sin((seed % 11 + frame_index) * 0.28) * 0.01), 3)
        z = round(base_z + (sin((seed % 13 + keypoint_index + frame_index) * 0.31) * 0.008), 3)
        return x, y, z
