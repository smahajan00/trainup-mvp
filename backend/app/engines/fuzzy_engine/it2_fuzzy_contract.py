from __future__ import annotations

from dataclasses import dataclass

IT2_FUZZY_VERSION = "phase4e_v0_1_0"


@dataclass(frozen=True)
class IT2UncertaintyConfig:
    base_uncertainty: float
    min_uncertainty: float
    max_uncertainty: float
    confidence_weight: float
    ambiguity_weight: float
    diagnostic_weight: float
    low_uncertainty_threshold: float
    medium_uncertainty_threshold: float

    def validate(self) -> None:
        if not 0.0 <= self.base_uncertainty <= 1.0:
            raise ValueError("base_uncertainty must be within [0,1].")
        if not 0.0 <= self.min_uncertainty <= self.max_uncertainty <= 1.0:
            raise ValueError("uncertainty bounds must satisfy 0 <= min <= max <= 1.")
        if any(
            value < 0.0
            for value in (
                self.confidence_weight,
                self.ambiguity_weight,
                self.diagnostic_weight,
            )
        ):
            raise ValueError("uncertainty weights must be non-negative.")
        if not (
            0.0 <= self.low_uncertainty_threshold
            < self.medium_uncertainty_threshold
            <= 1.0
        ):
            raise ValueError(
                "uncertainty category thresholds must satisfy 0 <= low < medium <= 1."
            )


DEFAULT_IT2_UNCERTAINTY_CONFIG = IT2UncertaintyConfig(
    base_uncertainty=0.05,
    min_uncertainty=0.03,
    max_uncertainty=0.35,
    confidence_weight=0.25,
    ambiguity_weight=0.20,
    diagnostic_weight=0.08,
    low_uncertainty_threshold=0.12,
    medium_uncertainty_threshold=0.22,
)


def get_it2_uncertainty_config() -> IT2UncertaintyConfig:
    DEFAULT_IT2_UNCERTAINTY_CONFIG.validate()
    return DEFAULT_IT2_UNCERTAINTY_CONFIG
