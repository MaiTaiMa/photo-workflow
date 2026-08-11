"""
Skript: app/automation_readiness.py
Zweck: Aggregiert Batch-Validierungsreports zu einer rein auswertenden Readiness-Metrik.
Version: 1.0.0
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


READINESS_POLICY = {
    "minimum_evaluated_predictions": 100,
    "minimum_evaluable_batches": 3,
    "minimum_overall_agreement": 0.95,
    "minimum_keep_precision": 0.95,
    "minimum_reject_precision": 0.95,
}


def _non_negative_int(report: dict[str, Any], field: str) -> int:
    value = report.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"validation report field {field!r} must be a non-negative integer")
    return value


def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def build_readiness_report(reports: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Build a sample-weighted readiness report from validation report payloads."""
    report_list = list(reports)
    totals = {
        "evaluated_predictions": 0,
        "matching_predictions": 0,
        "predicted_keep": 0,
        "confirmed_keep": 0,
        "predicted_reject": 0,
        "confirmed_reject": 0,
        "excluded_review_predictions": 0,
        "unreviewed_predictions": 0,
    }
    evaluable_batch_count = 0

    for report in report_list:
        if not isinstance(report, dict):
            raise ValueError("validation reports must be mappings")
        evaluated = _non_negative_int(report, "evaluated_predictions")
        for field in totals:
            totals[field] += _non_negative_int(report, field)
        if evaluated > 0:
            evaluable_batch_count += 1

    overall_agreement = _ratio(
        totals["matching_predictions"], totals["evaluated_predictions"]
    )
    keep_precision = _ratio(totals["confirmed_keep"], totals["predicted_keep"])
    reject_precision = _ratio(totals["confirmed_reject"], totals["predicted_reject"])

    reasons: list[str] = []
    if totals["evaluated_predictions"] == 0:
        status = "not_evaluable"
        reasons.append("no evaluated predictions are available")
    else:
        if totals["evaluated_predictions"] < READINESS_POLICY["minimum_evaluated_predictions"]:
            reasons.append("evaluated prediction count is below policy minimum")
        if evaluable_batch_count < READINESS_POLICY["minimum_evaluable_batches"]:
            reasons.append("evaluable batch count is below policy minimum")
        if overall_agreement is None or overall_agreement < READINESS_POLICY["minimum_overall_agreement"]:
            reasons.append("overall agreement is below policy minimum")
        if keep_precision is None or keep_precision < READINESS_POLICY["minimum_keep_precision"]:
            reasons.append("keep precision is below policy minimum")
        if reject_precision is None or reject_precision < READINESS_POLICY["minimum_reject_precision"]:
            reasons.append("reject precision is below policy minimum")
        status = "ready" if not reasons else "not_ready"

    return {
        "schema_version": "1.0",
        "status": status,
        "policy": READINESS_POLICY.copy(),
        "report_count": len(report_list),
        "evaluable_batch_count": evaluable_batch_count,
        **totals,
        "overall_agreement": overall_agreement,
        "keep_precision": keep_precision,
        "reject_precision": reject_precision,
        "readiness_reasons": reasons,
        "aggregated_at": datetime.now(timezone.utc).isoformat(),
    }


def load_validation_reports(runtime_path: str | Path) -> list[dict[str, Any]]:
    """Load every validation report from the controlled runtime directory."""
    validation_dir = Path(runtime_path) / "automation" / "validation"
    if not validation_dir.exists():
        return []
    if not validation_dir.is_dir():
        raise ValueError("validation report path must be a directory")

    reports: list[dict[str, Any]] = []
    for path in sorted(validation_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid validation JSON: {path}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"validation report must be a mapping: {path}")
        reports.append(payload)
    return reports


def write_readiness_report(runtime_path: str | Path, report: dict[str, Any]) -> Path:
    """Atomically write the aggregate readiness report below controlled runtime data."""
    target = Path(runtime_path) / "automation" / "readiness.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=target.parent, delete=False
    ) as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temporary_path = Path(handle.name)
    os.replace(temporary_path, target)
    return target


def aggregate_readiness(runtime_path: str | Path) -> tuple[dict[str, Any], Path]:
    """Aggregate validation reports and persist the resulting diagnostic report."""
    report = build_readiness_report(load_validation_reports(runtime_path))
    return report, write_readiness_report(runtime_path, report)
