"""
Skript: tests/unit/test_gates.py
Zweck: Testet automatic_handoff_gate und auto_phase1_gate.
Version: 1.0.0
"""
from pathlib import Path
import pytest
from app.automatic_handoff_gate import check_automatic_handoff_gate
from app.auto_phase1_gate import check_auto_phase1_gate


# =============================================================================
# check_automatic_handoff_gate Tests
# =============================================================================

def test_handoff_gate_mode_off(tmp_path: Path) -> None:
    """Mode 'off' blockiert automatic_handoff."""
    config = {
        "automation": {"mode": "off", "policy_version": "1.0"},
        "paths": {"base_dir": str(tmp_path)},
    }
    ok, report = check_automatic_handoff_gate(config, tmp_path, tmp_path)
    assert ok is False
    assert report["gate_reason"] == "mode_not_handoff_capable"


def test_handoff_gate_mode_auto_phase2(tmp_path: Path) -> None:
    """Mode 'auto_phase2' erlaubt Handoff-Prüfung."""
    config = {
        "automation": {"mode": "auto_phase2", "policy_version": "1.0"},
        "paths": {"base_dir": str(tmp_path)},
    }
    ok, report = check_automatic_handoff_gate(config, tmp_path, tmp_path)
    assert ok is False
    assert report["gate_reason"] == "readiness_not_ready"


def test_handoff_gate_mode_full_auto(tmp_path: Path) -> None:
    """Mode 'full_auto' erlaubt Handoff-Prüfung."""
    config = {
        "automation": {"mode": "full_auto", "policy_version": "1.0"},
        "paths": {"base_dir": str(tmp_path)},
    }
    ok, report = check_automatic_handoff_gate(config, tmp_path, tmp_path)
    assert ok is False
    assert report["gate_reason"] == "readiness_not_ready"


def test_handoff_gate_policy_version_missing(tmp_path: Path) -> None:
    """Fehlende policy_version blockiert Handoff."""
    config = {
        "automation": {"mode": "auto_phase2"},
        "paths": {"base_dir": str(tmp_path)},
    }
    ok, report = check_automatic_handoff_gate(config, tmp_path, tmp_path)
    assert ok is False
    assert report["gate_reason"] == "policy_version_missing"


def test_handoff_gate_automation_config_missing(tmp_path: Path) -> None:
    """Fehlende automation-Config blockiert Handoff."""
    config = {
        "paths": {"base_dir": str(tmp_path)},
    }
    ok, report = check_automatic_handoff_gate(config, tmp_path, tmp_path)
    assert ok is False
    assert report["gate_reason"] == "automation_config_missing"


# =============================================================================
# check_auto_phase1_gate Tests
# =============================================================================

def test_phase1_gate_mode_off(tmp_path: Path) -> None:
    """Mode 'off' blockiert auto_phase1."""
    config = {
        "automation": {"mode": "off", "policy_version": "1.0"},
    }
    ok, report = check_auto_phase1_gate(config, tmp_path)
    assert ok is False
    assert report["gate_reason"] == "mode_is_not_auto_phase1"


def test_phase1_gate_mode_auto_phase1(tmp_path: Path) -> None:
    """Mode 'auto_phase1' erlaubt Gate-Prüfung."""
    config = {
        "automation": {"mode": "auto_phase1", "policy_version": "1.0"},
    }
    ok, report = check_auto_phase1_gate(config, tmp_path)
    assert ok is False
    assert report["gate_reason"] == "readiness_not_ready"


def test_phase1_gate_policy_version_missing(tmp_path: Path) -> None:
    """Fehlende policy_version blockiert auto_phase1."""
    config = {
        "automation": {"mode": "auto_phase1"},
    }
    ok, report = check_auto_phase1_gate(config, tmp_path)
    assert ok is False
    assert report["gate_reason"] == "policy_version_missing"


def test_phase1_gate_automation_config_missing(tmp_path: Path) -> None:
    """Fehlende automation-Config blockiert auto_phase1."""
    config = {}
    ok, report = check_auto_phase1_gate(config, tmp_path)
    assert ok is False
    assert report["gate_reason"] == "automation_config_missing"
