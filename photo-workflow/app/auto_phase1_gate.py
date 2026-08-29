# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/auto_phase1_gate.py
# PURPOSE:     Fail-closed Gate für auto_phase1-Betrieb.
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11
# CHANGES:
#   2026-08-26 | 1.0.0 | Initial: Gate-Logik für auto_phase1.
# =============================================================================


from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from app.automation_readiness import aggregate_readiness
from app.trust_override import TrustOverrideStore, TrustOverrideError


def check_auto_phase1_gate(
    config: Mapping[str, Any],
    runtime_path: str | Path,
) -> tuple[bool, dict[str, Any]]:
    """Prüfe, ob auto_phase1-Betrieb sicher erlaubt ist.

    Returns (ok, gate_report). Das Gate ist fail-closed:
    - mode muss "auto_phase1" sein
    - automation.policy_version muss gesetzt sein
    - Readiness für diese Policy muss "ready" sein
    - Trust-Override darf nicht aktiv sein
    """
    automation = config.get("automation")
    if not isinstance(automation, Mapping):
        return False, {"gate_ok": False, "gate_reason": "automation_config_missing"}

    mode = automation.get("mode")
    if mode != "auto_phase1":
        return False, {"gate_ok": False, "gate_reason": "mode_is_not_auto_phase1", "mode": mode}

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
            "overall_agreement": report.get("overall_agreement"),
        }

    # Trust-Override prüfen (fail-closed: aktiv sperrt)
    try:
        override_store = TrustOverrideStore(runtime_path, policy_version)
        if override_store.is_active():
            return False, {"gate_ok": False, "gate_reason": "trust_override_active"}
    except TrustOverrideError:
        # Fehler beim Lesen des Override → fail-closed
        return False, {"gate_ok": False, "gate_reason": "trust_override_check_failed"}

    return True, {"gate_ok": True, "mode": mode, "policy_version": policy_version}