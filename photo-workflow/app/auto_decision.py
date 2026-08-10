"""
Skript: app/auto_decision.py
Zweck: Erstellt sichere KI-Prognosen für den Review-Workflow.
Version: 1.1.0
"""

from typing import Any, Mapping


VALID_AUTOMATION_MODES = frozenset({
    "off",
    "shadow",
    "assisted",
    "auto_keep",
    "full_auto",
})


def predict_decision(
    *,
    personal_score: float | None,
    final_score: float | None,
    config: Mapping[str, Any],
) -> tuple[str, str]:
    """Return a non-operative keep, reject, or review prediction."""
    automation = config.get("automation")
    if not isinstance(automation, Mapping):
        raise ValueError("automation configuration is required")

    mode = automation.get("mode", "off")
    if mode not in VALID_AUTOMATION_MODES:
        raise ValueError(f"unsupported automation mode: {mode}")
    if mode == "off":
        return "review", "automation_off"

    if personal_score is None or final_score is None:
        return "review", "score_unavailable"

    keep_min = float(automation["keep_score_min"])
    reject_max = float(automation["reject_score_max"])
    if not 0.0 <= reject_max < keep_min <= 1.0:
        raise ValueError("automation thresholds must satisfy 0 <= reject < keep <= 1")

    if personal_score >= keep_min and final_score >= keep_min:
        return "keep", "high_confidence_keep"
    if personal_score <= reject_max and final_score <= reject_max:
        return "reject", "high_confidence_reject"
    return "review", "manual_review_zone"


class AutoDecider:
    """Compatibility wrapper around the non-operative prediction function."""

    def __init__(self, config: Mapping[str, Any]):
        self.config = config

    def predict_decision(
        self,
        *,
        personal_score: float | None,
        final_score: float | None,
    ) -> tuple[str, str]:
        """Create a prediction without altering a final review decision."""
        return predict_decision(
            personal_score=personal_score,
            final_score=final_score,
            config=self.config,
        )
