from __future__ import annotations

from dataclasses import dataclass

FUZZY_INTERPRETATION_VERSION = "phase4a_v0_1_0"

FUZZY_BASE_LABELS = (
    "IDEAL",
    "SLIGHTLY_OFF",
    "MODERATELY_OFF",
    "STRONGLY_OFF",
)


@dataclass(frozen=True)
class FuzzyDeviationBands:
    """Deviation breakpoints for inspectable trapezoidal/triangular membership."""

    ideal_max: float
    slight_peak: float
    moderate_peak: float
    strong_min: float

    def validate(self) -> None:
        if not (
            0 <= self.ideal_max
            < self.slight_peak
            < self.moderate_peak
            < self.strong_min
        ):
            raise ValueError("Fuzzy deviation bands must be strictly increasing.")


DEFAULT_FUZZY_DEVIATION_BANDS = FuzzyDeviationBands(
    ideal_max=0.02,
    slight_peak=0.08,
    moderate_peak=0.18,
    strong_min=0.30,
)

# Metric-specific overrides can be added here without changing service logic.
METRIC_FUZZY_DEVIATION_BANDS: dict[str, FuzzyDeviationBands] = {}


def get_fuzzy_deviation_bands(metric_id: str | None) -> FuzzyDeviationBands:
    bands = METRIC_FUZZY_DEVIATION_BANDS.get(
        metric_id or "",
        DEFAULT_FUZZY_DEVIATION_BANDS,
    )
    bands.validate()
    return bands
