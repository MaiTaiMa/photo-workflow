"""Gate-Logik (Master-Prompt v13, 4.4)."""
from typing import Any

def check_phase1_gates(image_meta: dict[str, Any], config: dict[str, Any]) -> tuple[bool, list[str]]:
    errors = []
    min_score = config.get("phase1", {}).get("min_score", 0.7)
    score = image_meta.get("prediction_score")
    if score is None or score < min_score:
        if image_meta.get("trust_override") != "human_verified":
            errors.append(f"prediction_score {score} < {min_score}")
    return len(errors) == 0, errors

def check_phase2_gates(batch_meta: dict[str, Any], config: dict[str, Any]) -> tuple[bool, list[str]]:
    errors = []
    mode = config.get("automation", {}).get("mode", "off")
    if mode in ("auto_phase2", "full_auto"):
        if not config.get("phase2", {}).get("automatic_handoff", {}).get("enabled"):
            errors.append("automatic_handoff.enabled != true")
    if batch_meta.get("has_jpg_in_review"):
        errors.append("JPGs in Review")
    if batch_meta.get("has_analysis_error"):
        errors.append("analysis_error vorhanden")
    return len(errors) == 0, errors
