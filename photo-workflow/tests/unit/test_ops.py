# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_ops.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.runtime_control import RuntimeControl
from app.security_audit import audit_json_file
from app.strict_config import StrictConfigError, validate_strict_config


def base_config():
    return {"paths": {"base_dir": "/tmp/workflow"}, "safety": {}}


def test_active_api_requires_credentials(monkeypatch):
    config = base_config() | {"synology_api": {"enabled": True, "dry_run": False}}
    monkeypatch.delenv("SYNOLOGY_USER", raising=False)
    monkeypatch.delenv("SYNOLOGY_PASSWORD", raising=False)
    with pytest.raises(StrictConfigError):
        validate_strict_config(config)


def test_known_person_write_requires_pilot():
    config = base_config() | {"synology_api": {"enabled": True, "dry_run": True,
        "write_known_persons": True}}
    with pytest.raises(StrictConfigError):
        validate_strict_config(config)


def test_runtime_stop_is_safe_boundary():
    control = RuntimeControl()
    control.request_stop()
    assert control.before_expensive_step() is False
    control.mark_paused("wu-1")
    assert control.paused and control.current_workunit == "wu-1"


def test_security_audit_finds_embedding(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"embedding": [1, 2, 3]}))
    assert audit_json_file(path)