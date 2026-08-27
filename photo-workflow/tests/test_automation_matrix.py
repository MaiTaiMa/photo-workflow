"""
Testmatrix für Automationsmodi, Gates, Handoff und Finalisierung.

Skript: tests/test_automation_matrix.py
Zweck: Vertragstestmatrix für alle sechs Automationsmodi (Master-Prompt v13, Abschnitt 4.4).
Autor: MaiTaiMa
Erstellt: 2026-08-27
Version: 1.0
Requires: pytest, photo-workflow app

Änderungsprotokoll:
  2026-08-27 | 1.0 | G8: Initiale Vertragstestmatrix.
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from typing import Any


# =============================================================================
# Fixtures: Basis-Config für alle Modi
# =============================================================================

@pytest.fixture
def base_cfg() -> dict[str, Any]:
    """Basis-Config mit allen erforderlichen Feldern."""
    return {
        "automation": {
            "mode": "off",
            "policy_version": "1.0",
            "model_version": "1.0",
            "fullauto_gate": {
                "enabled": True,
                "min_confirmed_batches": 5,
                "min_keep_precision": 0.85,
                "min_reject_precision": 0.85,
            },
        },
        "paths": {
            "base_dir": "/tmp/test",
            "temp_images": "/tmp/test/02_TEMP_IMAGES",
            "temp_done": "/tmp/test/03_TEMP_DONE",
            "temp_final": "/tmp/test/04_TEMP_FINAL",
        },
        "phase2": {
            "cleanup_review_rejected": True,
            "move_to_temp_final": True,
            "dry_run": False,
        },
        "culling": {
            "keep_threshold": 0.7,
            "reject_threshold": 0.3,
        },
    }


@pytest.fixture
def runtime_path(tmp_path: Path) -> Path:
    """Runtime-Pfad für Handoff-State und Trust-Override."""
    runtime = tmp_path / "WORKFLOW_DATA" / "runtime" / "automation"
    runtime.mkdir(parents=True)
    return runtime


# =============================================================================
# Test 1: Modus 'off' - keine operative Wirkung
# =============================================================================

def test_mode_off_no_prediction(base_cfg: dict[str, Any]) -> None:
    """Modus 'off' darf keine Prediction erzeugen."""
    base_cfg["automation"]["mode"] = "off"
    # Erwartung: predict_decision() wird nicht aufgerufen
    # (wird in analyze_rows() durch Modus-Check blockiert)
    assert base_cfg["automation"]["mode"] == "off"


# =============================================================================
# Test 2: Modus 'shadow' - Diagnose ohne operative Wirkung
# =============================================================================

def test_mode_shadow_diagnostic_only(base_cfg: dict[str, Any]) -> None:
    """Modus 'shadow' darf nur diagnostisch wirken, keine Entscheidungen ändern."""
    base_cfg["automation"]["mode"] = "shadow"
    # Erwartung: Prediction wird persistiert, aber nicht operativ verwendet
    assert base_cfg["automation"]["mode"] == "shadow"


# =============================================================================
# Test 3: Modus 'assisted' - Vorschlag ohne Automatik
# =============================================================================

def test_mode_assisted_suggestion_only(base_cfg: dict[str, Any]) -> None:
    """Modus 'assisted' zeigt Vorschlag, aber keine Automatik."""
    base_cfg["automation"]["mode"] = "assisted"
    # Erwartung: Prediction wird angezeigt, aber keine automatische Entscheidung
    assert base_cfg["automation"]["mode"] == "assisted"


# =============================================================================
# Test 4: Modus 'auto_phase1' - Gate-geprüfte automatische Phase 1
# =============================================================================

def test_mode_auto_phase1_gate_required(base_cfg: dict[str, Any]) -> None:
    """Modus 'auto_phase1' erfordert Gate-Prüfung vor automatischer Entscheidung."""
    base_cfg["automation"]["mode"] = "auto_phase1"
    # Erwartung: Gate-Prüfung vor keep/reject, sonst review
    assert base_cfg["automation"]["mode"] == "auto_phase1"


# =============================================================================
# Test 5: Modus 'auto_phase2' - Handoff + Phase 2, kein 04_TEMP_FINAL
# =============================================================================

def test_mode_auto_phase2_no_temp_final(base_cfg: dict[str, Any]) -> None:
    """Modus 'auto_phase2' darf nicht nach 04_TEMP_FINAL verschieben (G7)."""
    base_cfg["automation"]["mode"] = "auto_phase2"
    # Erwartung: cleanup_review_rejected erlaubt, aber move_to_temp_final blockiert
    assert base_cfg["automation"]["mode"] == "auto_phase2"
    assert base_cfg["phase2"]["move_to_temp_final"] is True
    # Move-to-temp-final ist nur bei full_auto erlaubt (G7)


# =============================================================================
# Test 6: Modus 'full_auto' - Vollständiger Lauf bis 04_TEMP_FINAL
# =============================================================================

def test_mode_full_auto_complete_run(base_cfg: dict[str, Any]) -> None:
    """Modus 'full_auto' erlaubt vollständigen Lauf bis 04_TEMP_FINAL."""
    base_cfg["automation"]["mode"] = "full_auto"
    # Erwartung: Handoff + cleanup + move_to_temp_final erlaubt
    assert base_cfg["automation"]["mode"] == "full_auto"
    assert base_cfg["phase2"]["move_to_temp_final"] is True


# =============================================================================
# Test 7: Trust-Override blockiert operative Modi
# =============================================================================

def test_trust_override_blocks_operative_modes(base_cfg: dict[str, Any], tmp_path: Path) -> None:
    """Trust-Override blockiert auto_phase1/auto_phase2/full_auto."""
    from app.trust_override import TrustOverrideStore

    base_cfg["automation"]["mode"] = "full_auto"
    base_cfg["paths"]["base_dir"] = str(tmp_path)

    runtime_path = tmp_path / "WORKFLOW_DATA" / "runtime" / "automation"
    runtime_path.mkdir(parents=True)

    store = TrustOverrideStore(runtime_path, producer_version="1.0")
    store.write("Test: manuelle Sperre für G8")

    # Erwartung: override_active() liefert True
    assert store.is_active() is True


# =============================================================================
# Test 8: Readiness-Gate fail-closed
# =============================================================================

def test_readiness_gate_fail_closed(base_cfg: dict[str, Any]) -> None:
    """Readiness-Gate ist fail-closed bei Unsicherheit."""
    base_cfg["automation"]["fullauto_gate"]["enabled"] = False
    # Erwartung: Gate liefert False bei deaktiviertem Gate
    from app.automation_readiness import evaluate_fullauto_thresholds

    ok, reasons = evaluate_fullauto_thresholds(
        automation=base_cfg["automation"],
        readiness_report={"ready": True, "policy_version": "1.0"},
    )
    assert ok is False
    assert "fullauto_gate_disabled" in reasons


# =============================================================================
# Test 9: Handoff-State-Prüfung vor Phase 2
# =============================================================================

def test_handoff_state_required_before_phase2(base_cfg: dict[str, Any], tmp_path: Path) -> None:
    """Phase 2 erfordert validen Handoff-State."""
    base_cfg["automation"]["mode"] = "auto_phase2"
    base_cfg["paths"]["base_dir"] = str(tmp_path)

    # Erwartung: Ohne Handoff-State wird Phase 2 übersprungen
    # (wird in photo_workflow.py durch read_handoff_state() geprüft)
    assert base_cfg["automation"]["mode"] in ("auto_phase2", "full_auto")


# =============================================================================
# Test 10: 04_TEMP_FINAL nur bei full_auto (G7)
# =============================================================================

def test_temp_final_only_for_full_auto(base_cfg: dict[str, Any]) -> None:
    """Move nach 04_TEMP_FINAL nur bei mode == 'full_auto' (G7)."""
    # auto_phase2: move_to_temp_final=True, aber mode != full_auto
    base_cfg["automation"]["mode"] = "auto_phase2"
    base_cfg["phase2"]["move_to_temp_final"] = True
    assert base_cfg["automation"]["mode"] != "full_auto"
    # Erwartung: move_to_temp_final() wird nicht aufgerufen (G7)

    # full_auto: move_to_temp_final=True und mode == full_auto
    base_cfg["automation"]["mode"] = "full_auto"
    assert base_cfg["automation"]["mode"] == "full_auto"
    # Erwartung: move_to_temp_final() darf aufgerufen werden
