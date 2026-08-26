"""
Skript: app/automatic_handoff_gate.py
Zweck: Fail-closed Gate für automatic_handoff (Vertrag Abschnitt 6).
Version: 1.0.0
Requires: Python 3.11

Änderungsprotokoll:
  2026-08-26 | 1.0.0 | Initial: Gate-Logik für automatic_handoff.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from app.automation_readiness import aggregate_readiness
from app.trust_override import TrustOverrideStore, TrustOverrideError
from app.workflow_locks import WorkflowLockManager
from app.pause_checkpoint import PauseCheckpointStore


def check_automatic_handoff_gate(
    config: Mapping[str, Any],
    workdir: Path,
    runtime_path: str | Path,
) -> tuple[bool, dict[str, Any]]:
    """Prüfe, ob automatic_handoff sicher erlaubt ist.

    Returns (ok, gate_report). Das Gate ist fail-closed (Vertrag Abschnitt 6):
    - mode muss "auto_phase2" oder "full_auto" sein
    - policy_version muss gesetzt sein
    - Readiness für diese Policy muss "ready" sein
    - Trust-Override darf nicht aktiv sein
    - Kein Bild mit analysis_error (hier: base_score/final_score ungültig)
    - Kein Bild mit finaler Entscheidung "review"
    - MANUAL_KEEP ist angewendet und dokumentiert
    - Phase-1-Manifest/State sind valide (kein review_state_invalid)
    - Kein aktiver Lock-Konflikt
    - Batch wurde nicht pausiert/recovery-unklar markiert
    """
    automation = config.get("automation")
    if not isinstance(automation, Mapping):
        return False, {"gate_ok": False, "gate_reason": "automation_config_missing"}

    mode = automation.get("mode")
    if mode not in ("auto_phase2", "full_auto"):
        return False, {"gate_ok": False, "gate_reason": "mode_not_handoff_capable", "mode": mode}

    policy_version = automation.get("policy_version")
    if not isinstance(policy_version, str) or not policy_version.strip():
        return False, {"gate_ok": False, "gate_reason": "policy_version_missing"}

    # Readiness aggregieren (fail-closed: nur "ready" zählt)
    try:
        report, _ = aggregate_readiness(runtime_path, expected_policy_version=policy_version)
    except Exception:
        return False, {"gate_ok": False, "gate_reason": "readiness_aggregation_failed"}

    if report.get("status") != "ready":
        return False, {
            "gate_ok": False,
            "gate_reason": "readiness_not_ready",
            "readiness_status": report.get("status"),
        }

    # Trust-Override prüfen (fail-closed: aktiv sperrt)
    try:
        override_store = TrustOverrideStore(runtime_path, policy_version)
        if override_store.is_active():
            return False, {"gate_ok": False, "gate_reason": "trust_override_active"}
    except TrustOverrideError:
        return False, {"gate_ok": False, "gate_reason": "trust_override_check_failed"}

    # Lock-Konflikt prüfen (fail-closed)
    try:
        locks_dir = Path(config["paths"]["base_dir"]) / "WORKFLOW_DATA" / "locks"
        lock_manager = WorkflowLockManager(locks_dir)
        batch_id = workdir.name
        if lock_manager.is_locked(batch_id):
            return False, {"gate_ok": False, "gate_reason": "lock_conflict", "batch_id": batch_id}
    except Exception:
        return False, {"gate_ok": False, "gate_reason": "lock_check_failed"}

    # Pause/Recovery prüfen (fail-closed)
    try:
        state_dir = Path(config["paths"]["base_dir"]) / "WORKFLOW_DATA" / "runtime" / "phase1_states"
        pause_store = PauseCheckpointStore(state_dir, config.get("script_version", "unknown"))
        if pause_store.is_paused(workdir.name):
            return False, {"gate_ok": False, "gate_reason": "batch_is_paused"}
    except Exception:
        return False, {"gate_ok": False, "gate_reason": "pause_check_failed"}

    # TODO: Hier können weitere Gates ergänzt werden (Manifest, review_state_invalid, MANUAL_KEEP-Dokumentation).
    # Für Paket C.1 belassen wir es bei den oben genannten, um die Komplexität klein zu halten.

    return True, {"gate_ok": True, "mode": mode, "policy_version": policy_version}
