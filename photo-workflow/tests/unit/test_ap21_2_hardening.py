from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.archive_contract import create_verified_zip
from app.archive_verification import verify_zip_against_source
from app.phase2_contract import Phase2GateError, authorize_arw_cleanup
from app.state_store import StateStore
from app.state_validation import StateValidationError, validate_current_state


def test_state_hash_tampering_is_detected(tmp_path: Path):
    store = StateStore(tmp_path / "state")
    record = store.write("b+12345678", "phase1_completed", producer_version="test")
    path = store.path_for("b+12345678")
    value = json.loads(path.read_text())
    value["state"] = "phase2_completed"
    path.write_text(json.dumps(value))
    with pytest.raises(StateValidationError):
        validate_current_state(store, record["batch_id"])


def test_archive_bytes_and_hash_are_verified(tmp_path: Path):
    source = tmp_path / "batch"
    source.mkdir()
    (source / "photo.arw").write_bytes(b"raw")
    manifest = create_verified_zip(source, tmp_path / "archive.zip", ["photo.arw"],
        batch_id="b+12345678", config_fingerprint="a" * 64, producer_version="test")
    verify_zip_against_source(manifest["archive_path"], source, manifest["entries"])
    (source / "photo.arw").write_bytes(b"changed")
    with pytest.raises(Exception):
        verify_zip_against_source(manifest["archive_path"], source, manifest["entries"])


def test_cleanup_gate_returns_only_manifest_arws(tmp_path: Path):
    source = tmp_path / "batch"
    source.mkdir()
    (source / "photo.arw").write_bytes(b"raw")
    (source / "photo.jpg").write_bytes(b"jpg")
    manifest = create_verified_zip(source, tmp_path / "archive.zip",
        ["photo.arw", "photo.jpg"], batch_id="b+12345678",
        config_fingerprint="a" * 64, producer_version="test")
    store = StateStore(tmp_path / "state")
    store.write("b+12345678", "phase1_completed", producer_version="test")
    result = authorize_arw_cleanup(store, "b+12345678", manifest, source)
    assert [path.name for path in result] == ["photo.arw"]


def test_cleanup_gate_blocks_wrong_state(tmp_path: Path):
    source = tmp_path / "batch"
    source.mkdir()
    (source / "photo.arw").write_bytes(b"raw")
    manifest = create_verified_zip(source, tmp_path / "archive.zip", ["photo.arw"],
        batch_id="b+12345678", config_fingerprint="a" * 64, producer_version="test")
    store = StateStore(tmp_path / "state")
    store.write("b+12345678", "phase1_started", producer_version="test")
    with pytest.raises(Phase2GateError):
        authorize_arw_cleanup(store, "b+12345678", manifest, source)
