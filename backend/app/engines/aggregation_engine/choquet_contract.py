from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Mapping

CHOQUET_VERSION = "phase4d_v0_1_0"


@dataclass(frozen=True)
class ChoquetInteractionGroupConfig:
    group_id: str
    base_concepts: tuple[str, ...]
    singleton_weights: dict[str, float]
    synergy_bonus: float
    max_capacity: float = 1.0


@dataclass(frozen=True)
class ChoquetMetricIntensityConfig:
    severe_floor: float
    moderate_floor: float
    deviation_scale: float
    fuzzy_label_multipliers: dict[str, float]


CHOQUET_METRIC_INTENSITY_CONFIG = ChoquetMetricIntensityConfig(
    severe_floor=0.75,
    moderate_floor=0.45,
    deviation_scale=0.25,
    fuzzy_label_multipliers={
        "IDEAL": 0.0,
        "SLIGHTLY_OFF": 0.5,
        "MODERATELY_OFF": 0.75,
        "STRONGLY_OFF": 1.0,
        "NOT_INTERPRETABLE": 0.0,
    },
)


CONCEPT_INTERACTION_GROUPS: dict[str, ChoquetInteractionGroupConfig] = {
    "lower_body_control": ChoquetInteractionGroupConfig(
        group_id="lower_body_control",
        base_concepts=("depth", "mobility", "control"),
        singleton_weights={
            "depth": 0.34,
            "mobility": 0.33,
            "control": 0.33,
        },
        synergy_bonus=0.18,
    ),
    "postural_stability": ChoquetInteractionGroupConfig(
        group_id="postural_stability",
        base_concepts=("posture", "balance", "stability"),
        singleton_weights={
            "posture": 0.34,
            "balance": 0.33,
            "stability": 0.33,
        },
        synergy_bonus=0.15,
    ),
    "upper_body_alignment": ChoquetInteractionGroupConfig(
        group_id="upper_body_alignment",
        base_concepts=("alignment", "extension", "symmetry"),
        singleton_weights={
            "alignment": 0.4,
            "extension": 0.35,
            "symmetry": 0.25,
        },
        synergy_bonus=0.12,
    ),
    "coordinated_timing": ChoquetInteractionGroupConfig(
        group_id="coordinated_timing",
        base_concepts=("coordination", "control", "follow_through"),
        singleton_weights={
            "coordination": 0.4,
            "control": 0.35,
            "follow_through": 0.25,
        },
        synergy_bonus=0.14,
    ),
}


BODY_REGION_INTERACTION_CONFIG: dict[str, ChoquetInteractionGroupConfig] = {
    "lower_body": ChoquetInteractionGroupConfig(
        group_id="lower_body",
        base_concepts=(
            "depth",
            "mobility",
            "control",
            "balance",
            "alignment",
            "coordination",
            "extension",
            "follow_through",
            "stability",
        ),
        singleton_weights={
            "depth": 0.14,
            "mobility": 0.12,
            "control": 0.14,
            "balance": 0.12,
            "alignment": 0.12,
            "coordination": 0.12,
            "extension": 0.1,
            "follow_through": 0.07,
            "stability": 0.07,
        },
        synergy_bonus=0.12,
    ),
    "upper_body": ChoquetInteractionGroupConfig(
        group_id="upper_body",
        base_concepts=("alignment", "extension", "symmetry", "control", "stability"),
        singleton_weights={
            "alignment": 0.28,
            "extension": 0.22,
            "symmetry": 0.18,
            "control": 0.18,
            "stability": 0.14,
        },
        synergy_bonus=0.1,
    ),
    "core": ChoquetInteractionGroupConfig(
        group_id="core",
        base_concepts=("posture", "stability", "balance", "control"),
        singleton_weights={
            "posture": 0.35,
            "stability": 0.25,
            "balance": 0.2,
            "control": 0.2,
        },
        synergy_bonus=0.12,
    ),
}


OVERALL_REGION_CHOQUET_CONFIG = ChoquetInteractionGroupConfig(
    group_id="overall_session",
    base_concepts=("lower_body", "upper_body", "core"),
    singleton_weights={
        "lower_body": 0.4,
        "upper_body": 0.25,
        "core": 0.35,
    },
    synergy_bonus=0.1,
)


def _powerset(elements: tuple[str, ...]) -> list[frozenset[str]]:
    subsets = [frozenset()]
    for subset_size in range(1, len(elements) + 1):
        subsets.extend(
            frozenset(combo) for combo in combinations(elements, subset_size)
        )
    return subsets


def build_capacity(
    *,
    elements: list[str] | tuple[str, ...],
    singleton_weights: Mapping[str, float],
    synergy_bonus: float,
    max_capacity: float = 1.0,
) -> dict[frozenset[str], float]:
    ordered_elements = tuple(dict.fromkeys(elements))
    if not ordered_elements:
        return {frozenset(): 0.0}
    if max_capacity <= 0:
        raise ValueError("max_capacity must be positive.")
    if synergy_bonus < 0:
        raise ValueError("synergy_bonus must be non-negative.")

    raw_weights = {element: max(float(singleton_weights.get(element, 0.0)), 0.0) for element in ordered_elements}
    if all(weight == 0.0 for weight in raw_weights.values()):
        equal_weight = 1.0 / len(ordered_elements)
        raw_weights = {element: equal_weight for element in ordered_elements}
    else:
        total_weight = sum(raw_weights.values())
        raw_weights = {
            element: weight / total_weight for element, weight in raw_weights.items()
        }

    capacity: dict[frozenset[str], float] = {}
    full_set = frozenset(ordered_elements)
    for subset in _powerset(ordered_elements):
        if not subset:
            capacity[subset] = 0.0
            continue
        base_weight = sum(raw_weights[element] for element in subset)
        interaction_ratio = 0.0
        if len(ordered_elements) > 1 and len(subset) > 1:
            interaction_ratio = (len(subset) - 1) / (len(ordered_elements) - 1)
        capacity[subset] = round(
            min(max_capacity, base_weight + (synergy_bonus * interaction_ratio)),
            4,
        )
    capacity[full_set] = 1.0
    validate_capacity(capacity=capacity, universe=full_set)
    return capacity


def validate_capacity(
    *,
    capacity: Mapping[frozenset[str], float],
    universe: frozenset[str],
) -> None:
    expected_subsets = set(_powerset(tuple(sorted(universe))))
    if set(capacity.keys()) != expected_subsets:
        missing = expected_subsets - set(capacity.keys())
        extra = set(capacity.keys()) - expected_subsets
        raise ValueError(
            f"Capacity keys do not match universe subsets. Missing={missing}, extra={extra}"
        )

    if round(float(capacity[frozenset()]), 6) != 0.0:
        raise ValueError("Choquet capacity must satisfy g(empty)=0.")
    if round(float(capacity[universe]), 6) != 1.0:
        raise ValueError("Choquet capacity must satisfy g(all)=1.")

    for subset, value in capacity.items():
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"Capacity value for {subset} is outside [0,1].")

    ordered_subsets = list(expected_subsets)
    for subset_a in ordered_subsets:
        for subset_b in ordered_subsets:
            if subset_a.issubset(subset_b) and float(capacity[subset_a]) > float(
                capacity[subset_b]
            ) + 1e-9:
                raise ValueError(
                    f"Capacity is not monotonic for {subset_a} ⊆ {subset_b}."
                )


def choquet_integral(
    *,
    values: Mapping[str, float],
    capacity: Mapping[frozenset[str], float],
) -> float:
    if not values:
        return 0.0

    ordered_values = sorted(values.items(), key=lambda item: item[1])
    universe = frozenset(values.keys())
    validate_capacity(capacity=capacity, universe=universe)

    for _, value in ordered_values:
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError("Choquet values must stay within [0,1].")

    previous_value = 0.0
    result = 0.0
    for index, (_, current_value) in enumerate(ordered_values):
        remaining_set = frozenset(
            element for element, _ in ordered_values[index:]
        )
        result += (float(current_value) - previous_value) * float(
            capacity[remaining_set]
        )
        previous_value = float(current_value)
    return round(result, 4)
