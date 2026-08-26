"""Pure Phase-1 culling analysis with injected dependencies only."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable
@dataclass(frozen=True)
class Phase1AnalysisResult:
    rows: list[dict[str, Any]]
    predictions: list[dict[str, Any]]
def combine_scores(base_score: float, eye_score: float | None, personal_score: float | None, family_score: float | None, cfg: dict[str, Any]) -> float:
    weights = cfg.get("culling", {}).get("component_weights", {})
    active = {"base_score": base_score, "eye_score": eye_score, "personal_score": personal_score, "family_score": family_score}
    weighted = {key: float(weights.get(key, 0.0)) for key, value in active.items() if value is not None and float(weights.get(key, 0.0)) > 0}
    total_weight = sum(weighted.values())
    if total_weight <= 0:
        return max(0.0, min(1.0, float(base_score)))
    return max(0.0, min(1.0, sum(float(active[key]) * weighted[key] for key in weighted) / total_weight))
def analyze_rows(*, images: Iterable[Path], cfg: dict[str, Any], manual_keep_names: set[str], score: Callable[[Path], dict[str, Any]], detect_family: Callable[[Path], dict[str, Any]], predict: Callable[[dict[str, Any]], dict[str, Any]], apply_series: Callable[[list[dict[str, Any]]], list[dict[str, Any]]]) -> Phase1AnalysisResult:
    """Build final analysis rows without any filesystem mutation."""
    culling = cfg["culling"]
    keep_threshold = float(culling["keep_threshold"])
    reject_threshold = float(culling["reject_threshold"])
    family_enabled = bool(cfg.get("family_recognition", {}).get("enabled", False))
    rows, predictions = [], []
    for image in images:
        scored = score(image)
        family = detect_family(image)
        manual_keep = image.name in manual_keep_names
        family_score = float(family.get("family_score", 0.0)) if family_enabled else None
        final = 1.0 if manual_keep else combine_scores(scored["base_score"], scored.get("eye_score"), scored.get("personal_score"), family_score, cfg)
        decision, reason, protected = "keep", "manual_keep_match" if manual_keep else "score_keep", False
        if not manual_keep and final < reject_threshold:
            if family.get("protected_by_family_rule", False): decision, reason, protected = "review", "family_protected_score", True
            else: decision, reason = "reject", "score_reject"
        elif not manual_keep and final < keep_threshold: decision, reason = "review", "score_review"
        row = {"file": image.name, "generic_score": scored.get("generic_score"), "base_score": scored["base_score"], "personal_score": scored.get("personal_score"), "eye_score": scored.get("eye_score"), "family_score": family_score if family_score is not None else "", "final_score": round(final, 4), "decision": decision, "decision_reason": reason, "manual_keep": manual_keep, "protected_by_family_rule": protected, "detected_people": "|".join(family.get("detected_people", [])), "face_status": family.get("status", ""), "_family_tags": family.get("tags", []), "_family_regions": family.get("regions", [])}
        prediction = predict(row)
        row["predicted_decision"] = prediction.get("predicted_decision")
        row["prediction_reason"] = prediction.get("prediction_reason")
        rows.append(row); predictions.append(prediction)
    rows = apply_series(rows)

    # -------------------------------------------------------------------------
    # Paket A.3.2: Serienfelder in predictions nachträglich einfügen
    # (Master-Prompt 4.6: erweiterte Auditfelder)
    # -------------------------------------------------------------------------
    enriched_predictions = []
    for row, pred in zip(rows, predictions):
        enriched = dict(pred)
        series_id = row.get("series_id")
        if series_id not in (None, "", "single"):
            enriched["series_id"] = series_id
            enriched["series_rank"] = row.get("series_rank")
            enriched["series_best"] = row.get("series_best")
        # prediction_id nur für vollständige Production-Predictions
        required_fields = ("schema_version","producer_version","batch_id","image_id","model_version","policy_version","predicted_decision","prediction_reason","personal_score","final_score","predicted_at")
        if all(k in enriched for k in required_fields):
            from app.automation_contract import build_prediction_id
            enriched["prediction_id"] = build_prediction_id(enriched)
        enriched_predictions.append(enriched)
    predictions = enriched_predictions
    for row in rows:
        if row.get("manual_keep"):
            row["decision"] = "keep"; row["decision_reason"] = "manual_keep_match"; row["final_score"] = 1.0
    return Phase1AnalysisResult(rows=rows, predictions=predictions)
