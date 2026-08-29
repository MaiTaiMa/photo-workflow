# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/automation_config.py
# PURPOSE:     Validiert den automation-Block der Workflow-Konfiguration.
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.2.0
# REQUIRES:    Python 3.11, app.auto_decision
# CHANGES:
#   2026-08-23 | 1.2.0 | C1.2.5: Optionalen Fullauto-Gate-Vertrag validiert.
#   2026-08-20 | 1.1.0 | A1: Policy-Version und Vertragsmodi validiert.
# =============================================================================


from typing import Any, Mapping

from app.auto_decision import VALID_AUTOMATION_MODES


REQUIRED_AUTOMATION_FIELDS = frozenset({
    "policy_version",
    "mode",
    "keep_score_min",
    "reject_score_max",
    "evaluation_window_days",
    "min_evaluated_batches",
    "min_evaluated_images",
    "min_overall_agreement",
    "min_keep_precision",
    "min_reject_precision",
})


def validate_automation_config(config: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a normalized automation configuration."""
    automation = config.get("automation")
    if not isinstance(automation, Mapping):
        raise ValueError("automation must be a mapping")

    missing = REQUIRED_AUTOMATION_FIELDS.difference(automation)
    if missing:
        raise ValueError(f"automation misses required fields: {sorted(missing)}")

    mode = automation["mode"]
    if mode not in VALID_AUTOMATION_MODES:
        raise ValueError(f"unsupported automation mode: {mode}")

    normalized = {
        "policy_version": _policy_version(automation),
        "mode": mode,
        "keep_score_min": _score(automation, "keep_score_min"),
        "reject_score_max": _score(automation, "reject_score_max"),
        "evaluation_window_days": _positive_int(automation, "evaluation_window_days"),
        "min_evaluated_batches": _positive_int(automation, "min_evaluated_batches"),
        "min_evaluated_images": _positive_int(automation, "min_evaluated_images"),
        "min_overall_agreement": _score(automation, "min_overall_agreement"),
        "min_keep_precision": _score(automation, "min_keep_precision"),
        "min_reject_precision": _score(automation, "min_reject_precision"),
        "fullauto_gate": _validate_fullauto_gate(automation.get("fullauto_gate")),
    }

    if normalized["reject_score_max"] >= normalized["keep_score_min"]:
        raise ValueError("reject_score_max must be lower than keep_score_min")

    return normalized


def _validate_fullauto_gate(value: Any) -> dict[str, Any]:
    """Validate and normalize the optional Fullauto gate configuration."""
    if value is None:
        return {
            "enabled": False,
            "auto_execute": False,
            "fallback_mode": "assisted",
            "min_overall_agreement": 0.95,
            "min_batch_agreement": 0.90,
        }

    if not isinstance(value, Mapping):
        raise ValueError("fullauto_gate must be a mapping")

    enabled = value.get("enabled", False)
    auto_execute = value.get("auto_execute", False)
    fallback_mode = value.get("fallback_mode", "assisted")

    if not isinstance(enabled, bool):
        raise ValueError("fullauto_gate.enabled must be a boolean")
    if not isinstance(auto_execute, bool):
        raise ValueError("fullauto_gate.auto_execute must be a boolean")
    if fallback_mode != "assisted":
        raise ValueError("fullauto_gate.fallback_mode must be assisted")

    return {
        "enabled": enabled,
        "auto_execute": auto_execute,
        "fallback_mode": fallback_mode,
        "min_overall_agreement": _score(
            value,
            "min_overall_agreement",
            default=0.95,
        ),
        "min_batch_agreement": _score(
            value,
            "min_batch_agreement",
            default=0.90,
        ),
    }


def _policy_version(values: Mapping[str, Any]) -> str:
    """Validate a non-empty, versioned automation policy identifier."""
    value = values["policy_version"]
    if not isinstance(value, str) or not value.strip():
        raise ValueError("policy_version must be a non-empty string")
    return value.strip()


def _score(
    values: Mapping[str, Any],
    field: str,
    *,
    default: float | None = None,
) -> float:
    if field not in values:
        if default is None:
            raise ValueError(f"{field} is required")
        return default
    value = values[field]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number between 0.0 and 1.0")
    score = float(value)
    if not 0.0 <= score <= 1.0:
        raise ValueError(f"{field} must be a number between 0.0 and 1.0")
    return score


def _positive_int(values: Mapping[str, Any], field: str) -> int:
    value = values[field]
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value