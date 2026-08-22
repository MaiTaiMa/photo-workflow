"""
Skript: app/automation_readiness.py
Zweck: Aggregiert Batch-Validierungsreports zu einer rein auswertenden Readiness-Metrik.
Version: 1.2.0

Änderungsprotokoll:
  2026-08-22 | 1.2.0 | C1.2.4: Fullauto-Gate (fail-closed, ohne operative Wirkung) ergänzt.
  2026-08-22 | 1.1.0 | C1.2.4: Readiness filterbar nach Policy-Version.

Änderungsprotokoll:
  2026-08-22 | 1.1.0 | C1.2.4: Readiness filterbar nach Policy-Version.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping
from pathlib import Path


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


def build_readiness_report(
    reports: Iterable[dict[str, Any]],
    *,
    expected_policy_version: str | None = None,
) -> dict[str, Any]:
    """Build a sample-weighted readiness report from validation report payloads.

    Only reports whose policy_version matches expected_policy_version are counted
    as sufficient evidence. If expected_policy_version is None, all reports are used.
    """
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
        policy = report.get("policy_version")
        if expected_policy_version is not None and policy != expected_policy_version:
            continue
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


def aggregate_readiness(
    runtime_path: str | Path,
    *,
    expected_policy_version: str | None = None,
) -> tuple[dict[str, Any], Path]:
    """Aggregate validation reports and persist the resulting diagnostic report.

    Only reports whose policy_version matches expected_policy_version are counted
    as sufficient evidence for readiness.
    """
    report = build_readiness_report(
        load_validation_reports(runtime_path),
        expected_policy_version=expected_policy_version,
    )
    return report, write_readiness_report(runtime_path, report)


def is_fullauto_ready(
    config: Mapping[str, Any],
    runtime_path: str | Path,
) -> tuple[bool, dict[str, Any]]:
    """Determine whether fullauto is ready for the active policy.

    Returns (is_ready, readiness_report). The gate is fail-closed:
    - mode must be exactly "fullauto"
    - automation.policy_version must be a non-empty string
    - readiness for that exact policy_version must report status "ready"
    """
    automation = config.get("automation")
    if not isinstance(automation, Mapping):
        raise ValueError("automation configuration is required")

    mode = automation.get("mode")
    if mode != "fullauto":
        report = {
            "schema_version": "1.0",
            "status": "not_ready",
            "gate_reason": "mode_is_not_fullauto",
            "mode": mode,
            "aggregated_at": datetime.now(timezone.utc).isoformat(),
        }
        return False, report

    policy_version = automation.get("policy_version")
    if not isinstance(policy_version, str) or not policy_version.strip():
        report = {
            "schema_version": "1.0",
            "status": "not_ready",
            "gate_reason": "policy_version_missing",
            "mode": mode,
            "aggregated_at": datetime.now(timezone.utc).isoformat(),
        }
        return False, report

    report, _ = aggregate_readiness(
        runtime_path,
        expected_policy_version=policy_version,
    )
    if report.get("status") == "ready":
        report["expected_policy_version"] = policy_version
        report["mode"] = mode
        return True, report

    report["gate_reason"] = "readiness_not_ready_for_policy"
    report["mode"] = mode
    report["expected_policy_version"] = policy_version
    return False, report
