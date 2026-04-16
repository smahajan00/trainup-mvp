from __future__ import annotations

from collections.abc import Iterable

from app.models.enums import SkillLevel


class SeedValidationError(ValueError):
    """Raised when seed definitions are incomplete or internally inconsistent."""


def _ensure_non_empty_string(value: object, field_name: str, context: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise SeedValidationError(f"{context}: '{field_name}' must be a non-empty string.")


def _ensure_non_empty_list(value: object, field_name: str, context: str) -> list[object]:
    if not isinstance(value, list) or not value:
        raise SeedValidationError(f"{context}: '{field_name}' must be a non-empty list.")
    return value


def _validate_reference_payload(reference_payload: object, context: str) -> None:
    if not isinstance(reference_payload, dict) or not reference_payload:
        raise SeedValidationError(f"{context}: 'reference_payload' must be a non-empty object.")

    required_keys = {
        "movement_type",
        "phases",
        "tracked_joints",
        "ideal_ranges",
        "stability_expectations",
        "notes",
    }
    missing_keys = required_keys - set(reference_payload.keys())
    if missing_keys:
        raise SeedValidationError(
            f"{context}: reference_payload is missing required keys: {sorted(missing_keys)}."
        )

    movement_type = reference_payload["movement_type"]
    if movement_type not in {"static", "dynamic"}:
        raise SeedValidationError(
            f"{context}: reference_payload.movement_type must be 'static' or 'dynamic'."
        )

    _ensure_non_empty_list(reference_payload["phases"], "reference_payload.phases", context)
    _ensure_non_empty_list(reference_payload["tracked_joints"], "reference_payload.tracked_joints", context)

    if not isinstance(reference_payload["ideal_ranges"], dict) or not reference_payload["ideal_ranges"]:
        raise SeedValidationError(f"{context}: reference_payload.ideal_ranges must be a non-empty object.")
    if not isinstance(reference_payload["stability_expectations"], dict) or not reference_payload["stability_expectations"]:
        raise SeedValidationError(
            f"{context}: reference_payload.stability_expectations must be a non-empty object."
        )

    _ensure_non_empty_string(reference_payload["notes"], "reference_payload.notes", context)


def _validate_target_metrics(
    target_metrics: object,
    valid_metric_names: set[str],
    context: str,
) -> list[str]:
    if not isinstance(target_metrics, dict) or not target_metrics:
        raise SeedValidationError(f"{context}: 'target_metrics' must be a non-empty object.")

    metrics = target_metrics.get("metrics")
    metrics_list = _ensure_non_empty_list(metrics, "target_metrics.metrics", context)

    normalized_metrics: list[str] = []
    for metric_name in metrics_list:
        _ensure_non_empty_string(metric_name, "target_metrics.metrics[]", context)
        if metric_name not in valid_metric_names:
            raise SeedValidationError(
                f"{context}: target metric '{metric_name}' does not exist in MetricType."
            )
        normalized_metrics.append(metric_name)

    if len(set(normalized_metrics)) != len(normalized_metrics):
        raise SeedValidationError(f"{context}: target_metrics.metrics contains duplicate metric names.")

    return normalized_metrics


def _validate_thresholds(thresholds: object, context: str) -> None:
    if not isinstance(thresholds, dict):
        raise SeedValidationError(f"{context}: coaching_rules.thresholds must be an object.")

    required = {"minor", "moderate", "severe"}
    missing = required - set(thresholds.keys())
    if missing:
        raise SeedValidationError(
            f"{context}: coaching_rules.thresholds is missing required keys: {sorted(missing)}."
        )

    minor = thresholds["minor"]
    moderate = thresholds["moderate"]
    severe = thresholds["severe"]
    if not all(isinstance(value, (int, float)) for value in (minor, moderate, severe)):
        raise SeedValidationError(f"{context}: coaching_rules.thresholds values must be numeric.")
    if not minor < moderate < severe:
        raise SeedValidationError(f"{context}: thresholds must satisfy minor < moderate < severe.")


def _validate_rule_checks(
    rule_checks: object,
    valid_metric_names: set[str],
    target_metric_names: Iterable[str],
    context: str,
) -> None:
    rule_check_list = _ensure_non_empty_list(rule_checks, "coaching_rules.rule_checks", context)
    if len(rule_check_list) < 3:
        raise SeedValidationError(f"{context}: coaching_rules.rule_checks must contain at least 3 checks.")

    target_metric_name_set = set(target_metric_names)
    required_fields = {
        "metric",
        "condition",
        "severity_weight",
        "issue_label",
        "coaching_cue",
    }

    for index, rule_check in enumerate(rule_check_list, start=1):
        if not isinstance(rule_check, dict):
            raise SeedValidationError(f"{context}: rule_check #{index} must be an object.")

        missing_fields = required_fields - set(rule_check.keys())
        if missing_fields:
            raise SeedValidationError(
                f"{context}: rule_check #{index} is missing required fields: {sorted(missing_fields)}."
            )

        metric_name = rule_check["metric"]
        _ensure_non_empty_string(metric_name, f"rule_check #{index}.metric", context)
        _ensure_non_empty_string(rule_check["condition"], f"rule_check #{index}.condition", context)
        _ensure_non_empty_string(rule_check["issue_label"], f"rule_check #{index}.issue_label", context)
        _ensure_non_empty_string(rule_check["coaching_cue"], f"rule_check #{index}.coaching_cue", context)

        if metric_name not in valid_metric_names:
            raise SeedValidationError(
                f"{context}: rule_check #{index} references unknown metric '{metric_name}'."
            )
        if metric_name not in target_metric_name_set:
            raise SeedValidationError(
                f"{context}: rule_check #{index} metric '{metric_name}' must also appear in target_metrics."
            )

        if "expected_min" not in rule_check and "expected_max" not in rule_check:
            raise SeedValidationError(
                f"{context}: rule_check #{index} must include expected_min or expected_max."
            )

        severity_weight = rule_check["severity_weight"]
        if not isinstance(severity_weight, (int, float)):
            raise SeedValidationError(
                f"{context}: rule_check #{index}.severity_weight must be numeric."
            )
        if not 0 < float(severity_weight) <= 1:
            raise SeedValidationError(
                f"{context}: rule_check #{index}.severity_weight must be between 0 and 1."
            )


def _validate_coaching_rules(
    coaching_rules: object,
    valid_metric_names: set[str],
    target_metric_names: list[str],
    context: str,
) -> None:
    if not isinstance(coaching_rules, dict) or not coaching_rules:
        raise SeedValidationError(f"{context}: 'coaching_rules' must be a non-empty object.")

    required_keys = {
        "thresholds",
        "rule_checks",
        "positive_cues",
        "recommendation_templates",
    }
    missing_keys = required_keys - set(coaching_rules.keys())
    if missing_keys:
        raise SeedValidationError(
            f"{context}: coaching_rules is missing required keys: {sorted(missing_keys)}."
        )

    _validate_thresholds(coaching_rules["thresholds"], context)
    _validate_rule_checks(
        coaching_rules["rule_checks"],
        valid_metric_names,
        target_metric_names,
        context,
    )
    _ensure_non_empty_list(coaching_rules["positive_cues"], "coaching_rules.positive_cues", context)
    _ensure_non_empty_list(
        coaching_rules["recommendation_templates"],
        "coaching_rules.recommendation_templates",
        context,
    )


def validate_drill_seed(drill_seed: dict[str, object], valid_metric_names: set[str]) -> None:
    context = f"Drill '{drill_seed.get('drill_name', '<unknown>')}'"

    _ensure_non_empty_string(drill_seed.get("drill_name"), "drill_name", context)
    _ensure_non_empty_string(drill_seed.get("description"), "description", context)

    difficulty_level = drill_seed.get("difficulty_level")
    if not isinstance(difficulty_level, SkillLevel):
        raise SeedValidationError(
            f"{context}: difficulty_level must be a SkillLevel enum value."
        )

    target_metric_names = _validate_target_metrics(
        drill_seed.get("target_metrics"),
        valid_metric_names,
        context,
    )
    _validate_reference_payload(drill_seed.get("reference_payload"), context)
    _validate_coaching_rules(
        drill_seed.get("coaching_rules"),
        valid_metric_names,
        target_metric_names,
        context,
    )
