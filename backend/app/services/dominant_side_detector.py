from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from app.engines.cognition_engine.phase2a_contract import get_phase2a_contract
from app.models.drill import Drill
from app.models.enums import DominantSide
from app.schemas.session import PoseFrameResponse, PoseSequenceResponse

DetectionMethod = Literal[
    "ankle_motion",
    "wrist_motion",
    "not_required",
    "insufficient_evidence",
]

VISIBILITY_THRESHOLD = 0.50
MIN_VISIBLE_SAMPLES = 3
MIN_TOTAL_MOTION = 0.03
MIN_CONFIDENCE = 0.20
LEG_DOMINANT_DRILL_IDS = frozenset({"instep_pass", "basic_shooting_form"})
ARM_DOMINANT_DRILL_IDS = frozenset({"set_shot_form"})


@dataclass(frozen=True)
class DominantSideDetectionResult:
    resolved_side: DominantSide | None
    confidence: float
    method: DetectionMethod
    diagnostic_flags: list[str]


class DominantSideDetector:
    def supports_auto_detection(self, *, drill: Drill) -> bool:
        contract = get_phase2a_contract(drill.drill_name)
        if contract is None:
            return False

        return contract.drill_id in LEG_DOMINANT_DRILL_IDS | ARM_DOMINANT_DRILL_IDS

    def is_side_dependent(self, *, drill: Drill) -> bool:
        contract = get_phase2a_contract(drill.drill_name)
        if contract is None:
            return False

        if contract.requires_dominant_side:
            return True

        if "dominant" in contract.segmentation_formula.lower():
            return True

        return any("dominant_side" in metric.computation for metric in contract.metric_contracts)

    def detect(
        self,
        *,
        drill: Drill,
        pose_sequence: PoseSequenceResponse,
    ) -> DominantSideDetectionResult:
        method = self._detection_method(drill=drill)
        if method is None:
            return DominantSideDetectionResult(
                resolved_side=None,
                confidence=0.0,
                method="not_required",
                diagnostic_flags=[],
            )

        if method == "ankle_motion":
            left_joint = "left_ankle"
            right_joint = "right_ankle"
        else:
            left_joint = "left_wrist"
            right_joint = "right_wrist"

        left_motion, left_observations = self._motion_magnitude(
            frames=pose_sequence.sequence_data,
            landmark_name=left_joint,
        )
        right_motion, right_observations = self._motion_magnitude(
            frames=pose_sequence.sequence_data,
            landmark_name=right_joint,
        )

        confidence = self._confidence(left_motion=left_motion, right_motion=right_motion)
        diagnostic_flags = [
            f"AUTO_DETECTION_METHOD:{method}",
            f"LEFT_MOTION:{left_motion:.4f}",
            f"RIGHT_MOTION:{right_motion:.4f}",
            f"LEFT_VISIBLE_SAMPLES:{left_observations}",
            f"RIGHT_VISIBLE_SAMPLES:{right_observations}",
        ]

        if left_observations < MIN_VISIBLE_SAMPLES or right_observations < MIN_VISIBLE_SAMPLES:
            diagnostic_flags.append("INSUFFICIENT_VISIBLE_SIDE_SAMPLES")
            return DominantSideDetectionResult(
                resolved_side=None,
                confidence=confidence,
                method="insufficient_evidence",
                diagnostic_flags=diagnostic_flags,
            )

        total_motion = left_motion + right_motion
        if total_motion < MIN_TOTAL_MOTION:
            diagnostic_flags.append("INSUFFICIENT_TOTAL_SIDE_MOTION")
            return DominantSideDetectionResult(
                resolved_side=None,
                confidence=confidence,
                method="insufficient_evidence",
                diagnostic_flags=diagnostic_flags,
            )

        if confidence < MIN_CONFIDENCE:
            diagnostic_flags.append("AMBIGUOUS_SIDE_MOTION")
            return DominantSideDetectionResult(
                resolved_side=None,
                confidence=confidence,
                method="insufficient_evidence",
                diagnostic_flags=diagnostic_flags,
            )

        return DominantSideDetectionResult(
            resolved_side=(
                DominantSide.LEFT if left_motion > right_motion else DominantSide.RIGHT
            ),
            confidence=confidence,
            method=method,
            diagnostic_flags=diagnostic_flags,
        )

    @staticmethod
    def _detection_method(*, drill: Drill) -> Literal["ankle_motion", "wrist_motion"] | None:
        contract = get_phase2a_contract(drill.drill_name)
        if contract is None:
            return None

        if contract.drill_id in LEG_DOMINANT_DRILL_IDS:
            return "ankle_motion"

        if contract.drill_id in ARM_DOMINANT_DRILL_IDS:
            return "wrist_motion"

        return None

    @staticmethod
    def _motion_magnitude(
        *,
        frames: list[PoseFrameResponse],
        landmark_name: str,
    ) -> tuple[float, int]:
        positions: list[tuple[float, float, float]] = []
        for frame in frames:
            if not frame.frame_valid:
                continue

            landmark = frame.landmarks.get(landmark_name)
            if landmark is None or landmark.visibility < VISIBILITY_THRESHOLD:
                continue

            positions.append((frame.timestamp_ms, landmark.x, landmark.y))

        if len(positions) < 2:
            return 0.0, len(positions)

        motion = 0.0
        for previous, current in zip(positions, positions[1:]):
            motion += math.hypot(current[1] - previous[1], current[2] - previous[2])

        return round(motion, 6), len(positions)

    @staticmethod
    def _confidence(*, left_motion: float, right_motion: float) -> float:
        total_motion = left_motion + right_motion
        if total_motion <= 0:
            return 0.0

        return round(abs(left_motion - right_motion) / total_motion, 4)
