# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_baseline.py
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

from app.batch_identity import batch_id
from app.config_schema import  ConfigError, config_fingerprint, validate_config_strict, get_test_config
from app.path_security import PathSecurityError, ensure_within
from app.state_store import StateStore


def test_batch_id_contains_eight_digit_fingerprint(tmp_path: Path):
    (tmp_path / "IMG_0001.JPG").write_bytes(b"image")
    value = batch_id(tmp_path)
    assert value.startswith(f"{tmp_path.name}+")
    assert len(value.rsplit("+", 1)[1]) == 8


def test_state_store_is_hash_chained_and_atomic(tmp_path: Path):
    store = StateStore(tmp_path / "state")
    first = store.write("batch+12345678", "phase1_started", producer_version="test")
    second = store.write("batch+12345678", "phase1_moving", producer_version="test")
    assert second["previous_state_hash"] == first["hash"]
    saved = json.loads((tmp_path / "state" / "batch+12345678.json").read_text())
    assert saved["hash"] == second["hash"]


def test_path_security_rejects_escape(tmp_path: Path):
    with pytest.raises(PathSecurityError):
        ensure_within(tmp_path / "base", tmp_path / "outside")


def test_config_requires_paths_and_safety():
    """Testet dass paths, runtime und safety Pflichtfelder sind"""
    
    # Leere Config → Error
    with pytest.raises(ConfigError):
        validate_config_strict({})
    
    # Config ohne safety → Error
    config_no_safety = {
        "paths": {"base_dir": "/tmp/workflow"},
        "runtime": {"lock_file": "/tmp/workflow/lock"},
    }
    with pytest.raises(ConfigError):
        validate_config_strict(config_no_safety)
    
    # Vollstaendige Config → OK
    config = get_test_config("/tmp/workflow")
    validate_config_strict(config)
    assert len(config_fingerprint(config)) == 64
