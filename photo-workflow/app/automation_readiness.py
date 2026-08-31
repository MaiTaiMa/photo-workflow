# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/automation_readiness.py
# PURPOSE:     Aggregiert Batch-Validierungen zu einer rein diagnostischen Readiness-Metrik.
# AUTHOR:      Matzethias
# DATE:        2026-08-22
# VERSION:     1.2.1
# REQUIRES:    Python 3.11, JSON, pathlib
# CHANGES:
#   2026-08-26 | 1.2.1 | Header und Funktionsdokumentation gemäß Implementierungsregeln ergänzt.
#   2026-08-22 | 1.2.0 | C1.2.4: Fullauto-Gate fail-closed und nicht-operativ ergänzt.
#   2026-08-22 | 1.1.0 | C1.2.4: Readiness nach Policy-Version filterbar gemacht.
# =============================================================================


import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping
from app.trust_override import TrustOverrideError, TrustOverrideStore
from app.trust_manager import TrustManager
from pathlib import Path


READINESS_POLICY = {
    "minimum_evaluated_predictions": 100,
    "minimum_evaluable_batches": 3,
    "minimum_overall_agreement": 0.95,
    "minimum_keep_precision": 0.95,
    "minimum_reject_precision": 0.95,
}


# -----------------------------------------------------------------------------
# Validiert numerische Zähler aus unvertrauenswürdigen Report-Payloads.
# Eingaben bleiben unverändert; Unsicherheit führt zu einem sicheren Ergebnis.
# -----------------------------------------------------------------------------

def _non_negative_int(report: dict[str, Any], field: str) -> int:
    value = report.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"validation report field {field!r} must be a non-negative integer")
    return value


# -----------------------------------------------------------------------------
# Berechnet sichere Quoten und vermeidet Division durch null.
# Eingaben bleiben unverändert; Unsicherheit führt zu einem sicheren Ergebnis.
# -----------------------------------------------------------------------------

def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


# -----------------------------------------------------------------------------
# Aggregiert nur validierte Batch-Evidenz zu einem Diagnosebericht.
# Eingaben bleiben unverändert; Unsicherheit führt zu einem sicheren Ergebnis.
# -----------------------------------------------------------------------------

def build_readiness_report(
    reports: Iterable[dict[str, Any]],
    *,
    expected_policy_version: str | None = None,
) -> dict[str, Any]:
    """Build a sample-weighted readiness report from validation report payloads.

    Only reports whose policy_version matches expected_policy_version are counted
    as sufficient evidence. If expected_policy_version is None, all reports are used.
    """
    # -------------------------------------------------------------------------
    # Eingabereports werden erst gesammelt und danach deterministisch ausgewertet.
    # So bleibt die Diagnose unabhängig von der Art des gelieferten Iterables.
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # Eingabereports werden erst gesammelt und danach deterministisch ausgewertet.
    # So bleibt die Diagnose unabhängig von der Art des gelieferten Iterables.
    # -------------------------------------------------------------------------
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
    batch_agreements: list[dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # Nur strukturell gültige Reports derselben aktiven Policy zählen als Evidenz.
    # Abweichende Policy-Versionen werden nicht still mit aktuellen Daten vermischt.
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # Nur strukturell gültige Reports derselben aktiven Policy zählen als Evidenz.
    # Abweichende Policy-Versionen werden nicht still mit aktuellen Daten vermischt.
    # -------------------------------------------------------------------------
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
            batch_agreements.append(
                {
                    "batch_id": report.get("batch_id"),
                    "policy_version": policy,
                    "evaluated_predictions": evaluated,
                    "matching_predictions": _non_negative_int(
                        report,
                        "matching_predictions",
                    ),
                    "agreement": _ratio(
                        _non_negative_int(report, "matching_predictions"),
                        evaluated,
                    ),
                }
            )

    # -------------------------------------------------------------------------
    # Gesamt- und Klassenpräzision werden getrennt berechnet und nachweisbar geführt.
    # Fehlende Nenner liefern None und verhindern später eine unzulässige Freigabe.
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # Gesamt- und Klassenpräzision werden getrennt berechnet und nachweisbar geführt.
    # Fehlende Nenner liefern None und verhindern später eine unzulässige Freigabe.
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # Der Rückgabereport enthält nur aggregierte Diagnosedaten ohne Bildinhalte.
    # Der Zeitstempel beschreibt den Auswertezeitpunkt, nicht eine operative Aktion.
    # -------------------------------------------------------------------------
    return {
        "schema_version": "1.0",
        "status": status,
        "policy": READINESS_POLICY.copy(),
        "report_count": len(report_list),
        "evaluable_batch_count": evaluable_batch_count,
        "batch_agreements": batch_agreements,
        "minimum_batch_agreement": min(
            (
                item["agreement"]
                for item in batch_agreements
                if item["agreement"] is not None
            ),
            default=None,
        ),
        **totals,
        "overall_agreement": overall_agreement,
        "keep_precision": keep_precision,
        "reject_precision": reject_precision,
        "readiness_reasons": reasons,
        "aggregated_at": datetime.now(timezone.utc).isoformat(),
    }


# -----------------------------------------------------------------------------
# Lädt kontrollierte Validation-JSONs aus dem Runtime-Bereich.
# Eingaben bleiben unverändert; Unsicherheit führt zu einem sicheren Ergebnis.
# -----------------------------------------------------------------------------

def load_validation_reports(runtime_path: str | Path) -> list[dict[str, Any]]:
    """Load every validation report from the controlled runtime directory."""
    # -------------------------------------------------------------------------
    # Ausschließlich der kontrollierte Validation-Unterordner wird als Quelle akzeptiert.
    # Fehlende Verzeichnisse bedeuten fehlende Evidenz und nicht eine implizite Freigabe.
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # Ausschließlich der kontrollierte Validation-Unterordner wird als Quelle akzeptiert.
    # Fehlende Verzeichnisse bedeuten fehlende Evidenz und nicht eine implizite Freigabe.
    # -------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# Persistiert den Diagnosebericht atomar ohne Entscheidungswirkung.
# Eingaben bleiben unverändert; Unsicherheit führt zu einem sicheren Ergebnis.
# -----------------------------------------------------------------------------

def write_readiness_report(runtime_path: str | Path, report: dict[str, Any]) -> Path:
    """Atomically write the aggregate readiness report below controlled runtime data."""
    # -------------------------------------------------------------------------
    # Die Diagnose wird über eine temporäre Datei atomar veröffentlicht.
    # Ein Abbruch darf daher keinen teilweise geschriebenen Readiness-Report erzeugen.
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # Die Diagnose wird über eine temporäre Datei atomar veröffentlicht.
    # Ein Abbruch darf daher keinen teilweise geschriebenen Readiness-Report erzeugen.
    # -------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# Verbindet Laden, Aggregation und atomare Diagnose-Persistenz.
# Eingaben bleiben unverändert; Unsicherheit führt zu einem sicheren Ergebnis.
# -----------------------------------------------------------------------------

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


# -----------------------------------------------------------------------------
# Prüft zusätzliche Fullauto-Schwellen ohne Seiteneffekte.
# Eingaben bleiben unverändert; Unsicherheit führt zu einem sicheren Ergebnis.
# -----------------------------------------------------------------------------

def evaluate_fullauto_thresholds(
    automation: Mapping[str, Any],
    readiness_report: Mapping[str, Any],
) -> tuple[bool, list[str]]:
    """Evaluate Fullauto-specific thresholds without side effects."""
    reasons: list[str] = []
    gate = automation.get("fullauto_gate")

    if not isinstance(gate, Mapping):
        return False, ["fullauto_gate_missing"]

    if gate.get("enabled") is not True:
        reasons.append("fullauto_gate_disabled")

    overall = readiness_report.get("overall_agreement")
    minimum_batch = readiness_report.get("minimum_batch_agreement")

    required_overall = gate.get("min_overall_agreement", 0.95)
    required_batch = gate.get("min_batch_agreement", 0.90)

    if not isinstance(overall, (int, float)) or isinstance(overall, bool):
        reasons.append("overall_agreement_missing")
    elif overall < required_overall:
        reasons.append("fullauto_overall_agreement_below_threshold")

    if not isinstance(minimum_batch, (int, float)) or isinstance(
        minimum_batch,
        bool,
    ):
        reasons.append("minimum_batch_agreement_missing")
    elif minimum_batch < required_batch:
        reasons.append("fullauto_batch_agreement_below_threshold")

    return not reasons, reasons


# -----------------------------------------------------------------------------
# Ermittelt fail-closed die Gate-Bereitschaft der aktiven Policy.
# Eingaben bleiben unverändert; Unsicherheit führt zu einem sicheren Ergebnis.
# -----------------------------------------------------------------------------

def is_fullauto_ready(
    config: Mapping[str, Any],
    runtime_path: str | Path,
) -> tuple[bool, dict[str, Any]]:
    """Determine whether full_auto is ready for the active policy.

    Returns (is_ready, readiness_report). The gate is fail-closed:
    - mode must be exactly "full_auto"
    - automation.policy_version must be a non-empty string
    - readiness for that exact policy_version must report status "ready"
    """
    # -------------------------------------------------------------------------
    # Ein fehlender Automation-Block ist keine Bereitschaft und wird explizit abgelehnt.
    # Die Gate-Prüfung startet erst nach erfolgreicher struktureller Konfigurationsprüfung.
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # Ein fehlender Automation-Block ist keine Bereitschaft und wird explizit abgelehnt.
    # Die Gate-Prüfung startet erst nach erfolgreicher struktureller Konfigurationsprüfung.
    # -------------------------------------------------------------------------
    automation = config.get("automation")
    if not isinstance(automation, Mapping):
        raise ValueError("automation configuration is required")

    mode = automation.get("mode")
    if mode != "full_auto":
        report = {
            "schema_version": "1.0",
            "status": "not_ready",
            "gate_reason": "mode_is_not_full_auto",
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

    # -------------------------------------------------------------------------
    # Readiness wird aus den Rohdaten neu aggregiert, nie aus manipulierten Altberichten.
    # Nur ein positiver Report der erwarteten Policy kann die nächste Gate-Prüfung erreichen.
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # Readiness wird aus den Rohdaten neu aggregiert, nie aus manipulierten Altberichten.
    # Nur ein positiver Report der erwarteten Policy kann die nächste Gate-Prüfung erreichen.
    # -------------------------------------------------------------------------
    report, _ = aggregate_readiness(
        runtime_path,
        expected_policy_version=policy_version,
    )
    if report.get("status") == "ready":
        gate_ready, gate_reasons = evaluate_fullauto_thresholds(
            automation,
            report,
        )
        report["expected_policy_version"] = policy_version
        report["mode"] = mode
        report["fullauto_gate_ready"] = gate_ready

        if gate_ready:
            try:
                override_store = TrustOverrideStore(
                    runtime_path,
                    str(automation.get("policy_version")),
                )
                override_active = override_store.is_active()
            except TrustOverrideError:
                report["gate_reason"] = "trust_override_invalid"
                report["gate_reasons"] = ["trust_override_invalid"]
                return False, report

            if override_active:
                report["gate_reason"] = "trust_override_active"
                report["gate_reasons"] = ["trust_override_active"]
                return False, report

            # TrustManager fuer batchbezogenes Vertrauen
            # HINWEIS: Batch-Pruefung erfolgt in check_automatic_handoff_gate(),
            # wo workdir verfuegbar ist. Hier nur globale Readiness.
            return True, report

        report["gate_reason"] = gate_reasons[0]
        report["gate_reasons"] = gate_reasons
        return False, report

    report["gate_reason"] = "readiness_not_ready_for_policy"
    report["mode"] = mode
    report["expected_policy_version"] = policy_version
    return False, report

# -----------------------------------------------------------------------------
# Formatiert einen menschenlesbaren Status-Block für den KI-Assistenten.
# Rein diagnostisch, keine Seiteneffekte, keine Freigabe-Entscheidung.
# -----------------------------------------------------------------------------

def format_ai_status_block(
    report: dict[str, Any],
    mode: str,
    batch_id: str,
    config_path: str = "config/config.yaml",
) -> str:
    """Baut einen abgesetzten Status-Block zum KI-Assistenten-Bereitschaftsgrad."""
    policy = report.get("policy", {})
    status = report.get("status", "unknown")
    ready = bool(report.get("fullauto_gate_ready", status == "ready"))

    def pct(value: Any) -> str:
        return f"{value * 100:.1f}%" if isinstance(value, (int, float)) else "n/a"

    gate_reason = report.get("gate_reason", status)
    lines = [
        "=" * 60,
        "🤖 KI-ASSISTENT STATUS",
        "=" * 60,
        f"Modus:                    {mode}",
        f"Batch:                    {batch_id}",
        f"Gate-Status:              {'✅ BEREIT' if ready else f'❌ NICHT BEREIT ({gate_reason})'}",
        "-" * 60,
        f"Validierte Batches:       {report.get('evaluable_batch_count', 0)} / {policy.get('minimum_evaluable_batches', '?')} (Minimum)",
        f"Ausgewertete Vorhersagen: {report.get('evaluated_predictions', 0)} / {policy.get('minimum_evaluated_predictions', '?')} (Minimum)",
        f"Gesamt-Übereinstimmung:   {pct(report.get('overall_agreement'))} (Ziel: >= {pct(policy.get('minimum_overall_agreement'))})",
        f"Keep-Präzision:           {pct(report.get('keep_precision'))} (Ziel: >= {pct(policy.get('minimum_keep_precision'))})",
        f"Reject-Präzision:         {pct(report.get('reject_precision'))} (Ziel: >= {pct(policy.get('minimum_reject_precision'))})",
    ]
    if not ready:
        lines += [
            "-" * 60,
            "Nächster Schritt:",
            f"  python -m app.photo_workflow --config {config_path} validate-reviews --batch {batch_id}",
        ]
    lines.append("=" * 60)
    return "\n".join(lines)
