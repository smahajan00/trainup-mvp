from __future__ import annotations

from dataclasses import dataclass

from app.engines.cognition_engine.phase2a_contract import PHASE2A_CONTRACTS_BY_DRILL_NAME

BODY_PART_TAXONOMY: dict[str, tuple[str, ...]] = {
    "lower_body": ("hip", "knee", "ankle", "foot"),
    "upper_body": ("shoulder", "elbow", "wrist"),
    "core": ("trunk", "spine"),
}

MOVEMENT_CONCEPT_TAXONOMY: tuple[str, ...] = (
    "stability",
    "balance",
    "alignment",
    "control",
    "mobility",
    "depth",
    "extension",
    "posture",
    "coordination",
    "follow_through",
    "symmetry",
)


@dataclass(frozen=True)
class OntologyMetricMapping:
    metric_id: str
    body_part: str
    concepts: tuple[str, ...]
    movement_group: str
    phase_context: str


PHASE2_SUPPORTED_METRIC_IDS: tuple[str, ...] = tuple(
    sorted(
        {
            metric.metric_id
            for contract in PHASE2A_CONTRACTS_BY_DRILL_NAME.values()
            for metric in contract.metric_contracts
        }
    )
)


ONTOLOGY_MAPPINGS_BY_METRIC_ID: dict[str, OntologyMetricMapping] = {
    "balance_stability": OntologyMetricMapping(
        metric_id="balance_stability",
        body_part="hip",
        concepts=("balance", "stability"),
        movement_group="lower_body_control",
        phase_context="multi_phase",
    ),
    "elbow_angle_consistency": OntologyMetricMapping(
        metric_id="elbow_angle_consistency",
        body_part="elbow",
        concepts=("alignment", "control"),
        movement_group="shooting_form",
        phase_context="load_follow_through",
    ),
    "elbow_extension": OntologyMetricMapping(
        metric_id="elbow_extension",
        body_part="elbow",
        concepts=("extension", "control"),
        movement_group="upper_body_pressing",
        phase_context="press",
    ),
    "hip_level_stability": OntologyMetricMapping(
        metric_id="hip_level_stability",
        body_part="hip",
        concepts=("stability", "balance"),
        movement_group="lower_body_control",
        phase_context="hold",
    ),
    "hip_stability": OntologyMetricMapping(
        metric_id="hip_stability",
        body_part="hip",
        concepts=("stability", "balance"),
        movement_group="lower_body_control",
        phase_context="descent",
    ),
    "instep_backswing_knee_angle": OntologyMetricMapping(
        metric_id="instep_backswing_knee_angle",
        body_part="knee",
        concepts=("mobility", "coordination"),
        movement_group="kicking_mechanics",
        phase_context="backswing",
    ),
    "instep_contact_extension": OntologyMetricMapping(
        metric_id="instep_contact_extension",
        body_part="knee",
        concepts=("extension", "coordination"),
        movement_group="kicking_mechanics",
        phase_context="contact",
    ),
    "instep_follow_through_stability": OntologyMetricMapping(
        metric_id="instep_follow_through_stability",
        body_part="ankle",
        concepts=("follow_through", "stability"),
        movement_group="kicking_mechanics",
        phase_context="follow_through",
    ),
    "instep_torso_tilt": OntologyMetricMapping(
        metric_id="instep_torso_tilt",
        body_part="trunk",
        concepts=("posture", "control"),
        movement_group="kicking_mechanics",
        phase_context="contact",
    ),
    "knee_alignment_score": OntologyMetricMapping(
        metric_id="knee_alignment_score",
        body_part="knee",
        concepts=("alignment", "control"),
        movement_group="lower_body_pattern",
        phase_context="descent",
    ),
    "knee_flexion": OntologyMetricMapping(
        metric_id="knee_flexion",
        body_part="knee",
        concepts=("depth", "mobility"),
        movement_group="lower_body_pattern",
        phase_context="hold_recovery",
    ),
    "lockout_control": OntologyMetricMapping(
        metric_id="lockout_control",
        body_part="shoulder",
        concepts=("control", "extension"),
        movement_group="upper_body_pressing",
        phase_context="lockout",
    ),
    "plant_foot_alignment_ratio": OntologyMetricMapping(
        metric_id="plant_foot_alignment_ratio",
        body_part="foot",
        concepts=("alignment", "balance"),
        movement_group="kicking_mechanics",
        phase_context="setup",
    ),
    "posture_accuracy": OntologyMetricMapping(
        metric_id="posture_accuracy",
        body_part="trunk",
        concepts=("posture", "stability"),
        movement_group="postural_control",
        phase_context="setup",
    ),
    "repetition_consistency": OntologyMetricMapping(
        metric_id="repetition_consistency",
        body_part="knee",
        concepts=("control", "coordination"),
        movement_group="lower_body_pattern",
        phase_context="ascent",
    ),
    "shooting_alignment": OntologyMetricMapping(
        metric_id="shooting_alignment",
        body_part="elbow",
        concepts=("alignment", "coordination"),
        movement_group="shooting_form",
        phase_context="load_release",
    ),
    "shooting_balance": OntologyMetricMapping(
        metric_id="shooting_balance",
        body_part="hip",
        concepts=("balance", "follow_through"),
        movement_group="kicking_mechanics",
        phase_context="follow_through",
    ),
    "shooting_contact_extension": OntologyMetricMapping(
        metric_id="shooting_contact_extension",
        body_part="knee",
        concepts=("extension", "coordination"),
        movement_group="kicking_mechanics",
        phase_context="contact",
    ),
    "shooting_knee_load": OntologyMetricMapping(
        metric_id="shooting_knee_load",
        body_part="knee",
        concepts=("depth", "mobility"),
        movement_group="kicking_mechanics",
        phase_context="load",
    ),
    "shooting_swing_velocity": OntologyMetricMapping(
        metric_id="shooting_swing_velocity",
        body_part="ankle",
        concepts=("coordination", "control"),
        movement_group="kicking_mechanics",
        phase_context="swing",
    ),
    "shoulder_control": OntologyMetricMapping(
        metric_id="shoulder_control",
        body_part="shoulder",
        concepts=("stability", "control"),
        movement_group="shooting_form",
        phase_context="release",
    ),
    "shoulder_symmetry": OntologyMetricMapping(
        metric_id="shoulder_symmetry",
        body_part="shoulder",
        concepts=("symmetry", "alignment"),
        movement_group="upper_body_pressing",
        phase_context="lockout",
    ),
    "stance_width_control": OntologyMetricMapping(
        metric_id="stance_width_control",
        body_part="foot",
        concepts=("balance", "alignment"),
        movement_group="lower_body_pattern",
        phase_context="setup_hold",
    ),
    "support_foot_distance_ratio": OntologyMetricMapping(
        metric_id="support_foot_distance_ratio",
        body_part="foot",
        concepts=("alignment", "balance"),
        movement_group="kicking_mechanics",
        phase_context="setup_contact",
    ),
    "torso_alignment": OntologyMetricMapping(
        metric_id="torso_alignment",
        body_part="trunk",
        concepts=("posture", "control"),
        movement_group="postural_control",
        phase_context="multi_phase",
    ),
    "torso_rotation_stability": OntologyMetricMapping(
        metric_id="torso_rotation_stability",
        body_part="trunk",
        concepts=("posture", "stability"),
        movement_group="kicking_mechanics",
        phase_context="follow_through",
    ),
    "wrist_elbow_alignment": OntologyMetricMapping(
        metric_id="wrist_elbow_alignment",
        body_part="wrist",
        concepts=("alignment", "control"),
        movement_group="upper_body_pressing",
        phase_context="press_return",
    ),
}


def get_ontology_mapping(metric_id: str) -> OntologyMetricMapping | None:
    return ONTOLOGY_MAPPINGS_BY_METRIC_ID.get(metric_id)


def validate_ontology_contract() -> None:
    taxonomy_body_parts = {
        body_part
        for body_parts in BODY_PART_TAXONOMY.values()
        for body_part in body_parts
    }
    supported_concepts = set(MOVEMENT_CONCEPT_TAXONOMY)
    missing_metric_ids = set(PHASE2_SUPPORTED_METRIC_IDS) - set(
        ONTOLOGY_MAPPINGS_BY_METRIC_ID.keys()
    )
    extra_metric_ids = set(ONTOLOGY_MAPPINGS_BY_METRIC_ID.keys()) - set(
        PHASE2_SUPPORTED_METRIC_IDS
    )
    if missing_metric_ids:
        raise ValueError(
            "Ontology mappings are missing metric ids: "
            + ", ".join(sorted(missing_metric_ids))
        )
    if extra_metric_ids:
        raise ValueError(
            "Ontology mappings contain unsupported metric ids: "
            + ", ".join(sorted(extra_metric_ids))
        )

    for metric_id, mapping in ONTOLOGY_MAPPINGS_BY_METRIC_ID.items():
        if mapping.body_part not in taxonomy_body_parts:
            raise ValueError(
                f"Ontology mapping for {metric_id} uses unknown body part {mapping.body_part}."
            )
        invalid_concepts = set(mapping.concepts) - supported_concepts
        if invalid_concepts:
            raise ValueError(
                f"Ontology mapping for {metric_id} uses unknown concepts: "
                + ", ".join(sorted(invalid_concepts))
            )
        if not mapping.concepts:
            raise ValueError(f"Ontology mapping for {metric_id} must define concepts.")


validate_ontology_contract()
