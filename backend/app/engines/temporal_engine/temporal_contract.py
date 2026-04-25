from __future__ import annotations

from dataclasses import dataclass

TEMPORAL_MODEL_VERSION = "phase4f_v0_1_0"


@dataclass(frozen=True)
class TemporalThresholdConfig:
    minimum_phase_frames: int
    minimum_phase_duration_ms: float
    incomplete_valid_frame_ratio: float
    uncertain_valid_frame_ratio: float
    uncertain_fuzzy_confidence_max: float
    stable_valid_frame_ratio: float
    stable_velocity_max: float
    stable_smoothness_min: float
    rushed_duration_ms: float
    rushed_velocity_min: float
    jerky_smoothness_max: float
    jerky_acceleration_min: float
    velocity_normalizer: float
    transition_gap_tolerance_ms: float
    default_keypoints: tuple[str, ...]
    body_region_keypoints: dict[str, tuple[str, ...]]

    def validate(self) -> None:
        if self.minimum_phase_frames < 1:
            raise ValueError("minimum_phase_frames must be >= 1.")
        if self.minimum_phase_duration_ms < 0 or self.rushed_duration_ms < 0:
            raise ValueError("phase duration thresholds must be non-negative.")
        for name, value in (
            ("incomplete_valid_frame_ratio", self.incomplete_valid_frame_ratio),
            ("uncertain_valid_frame_ratio", self.uncertain_valid_frame_ratio),
            ("uncertain_fuzzy_confidence_max", self.uncertain_fuzzy_confidence_max),
            ("stable_valid_frame_ratio", self.stable_valid_frame_ratio),
            ("stable_velocity_max", self.stable_velocity_max),
            ("stable_smoothness_min", self.stable_smoothness_min),
            ("rushed_velocity_min", self.rushed_velocity_min),
            ("jerky_smoothness_max", self.jerky_smoothness_max),
            ("jerky_acceleration_min", self.jerky_acceleration_min),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0,1].")
        if self.velocity_normalizer <= 0:
            raise ValueError("velocity_normalizer must be > 0.")
        if self.transition_gap_tolerance_ms < 0:
            raise ValueError("transition_gap_tolerance_ms must be non-negative.")
        if not self.default_keypoints:
            raise ValueError("default_keypoints must not be empty.")
        if not self.body_region_keypoints:
            raise ValueError("body_region_keypoints must not be empty.")


TEMPORAL_BODY_REGION_KEYPOINTS: dict[str, tuple[str, ...]] = {
    "lower_body": (
        "left_hip",
        "right_hip",
        "left_knee",
        "right_knee",
        "left_ankle",
        "right_ankle",
        "left_heel",
        "right_heel",
        "left_foot_index",
        "right_foot_index",
    ),
    "upper_body": (
        "left_shoulder",
        "right_shoulder",
        "left_elbow",
        "right_elbow",
        "left_wrist",
        "right_wrist",
    ),
    "core": (
        "nose",
        "left_shoulder",
        "right_shoulder",
        "left_hip",
        "right_hip",
    ),
}

DEFAULT_TEMPORAL_KEYPOINTS = (
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
)

DEFAULT_TEMPORAL_THRESHOLDS = TemporalThresholdConfig(
    minimum_phase_frames=2,
    minimum_phase_duration_ms=33.0,
    incomplete_valid_frame_ratio=0.55,
    uncertain_valid_frame_ratio=0.75,
    uncertain_fuzzy_confidence_max=0.55,
    stable_valid_frame_ratio=0.95,
    stable_velocity_max=0.25,
    stable_smoothness_min=0.72,
    rushed_duration_ms=120.0,
    rushed_velocity_min=0.62,
    jerky_smoothness_max=0.42,
    jerky_acceleration_min=0.30,
    velocity_normalizer=2.0,
    transition_gap_tolerance_ms=80.0,
    default_keypoints=DEFAULT_TEMPORAL_KEYPOINTS,
    body_region_keypoints=TEMPORAL_BODY_REGION_KEYPOINTS,
)


def get_temporal_threshold_config() -> TemporalThresholdConfig:
    DEFAULT_TEMPORAL_THRESHOLDS.validate()
    return DEFAULT_TEMPORAL_THRESHOLDS
