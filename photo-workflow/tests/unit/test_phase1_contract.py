from __future__ import annotations

from pathlib import Path

import pytest

from app.batch_layout import assert_review_state_valid, ensure_layout, validate_pairings
from app.inventory import collect_inventory, stable_inventory
from app.phase_state import PhaseTransitionError, transition
from app.state_store import StateStore


def test_phase1_state_machine_rejects_backward_transition(tmp_path: Path):
    store = StateStore(tmp_path / "state")
    transition(store, "batch+12345678", "phase1_started", producer_version="test")
    transition(store, "batch+12345678", "phase1_moving", producer_version="test")
    with pytest.raises(PhaseTransitionError):
        transition(store, "batch+12345678", "phase1_started", producer_version="test")


def test_stable_inventory_contains_content_hash(tmp_path: Path):
    image = tmp_path / "image.jpg"
    image.write_bytes(b"one")
    entries, fingerprint = stable_inventory(tmp_path, wait_seconds=0)
    assert entries[0].sha256
    assert len(fingerprint) == 64
    image.write_bytes(b"two")
    assert collect_inventory(tmp_path)[0].sha256 != entries[0].sha256


def test_layout_and_pairing_validation(tmp_path: Path):
    layout = ensure_layout(tmp_path)
    (tmp_path / "photo.jpg").write_bytes(b"jpg")
    (layout["ARW"] / "photo.arw").write_bytes(b"arw")
    assert validate_pairings(tmp_path) == []
    assert_review_state_valid(tmp_path)


def test_multiple_active_jpgs_are_blocking(tmp_path: Path):
    layout = ensure_layout(tmp_path)
    (tmp_path / "photo.jpg").write_bytes(b"one")
    (tmp_path / "photo.jpeg").write_bytes(b"two")
    (layout["ARW"] / "photo.arw").write_bytes(b"arw")
    assert validate_pairings(tmp_path)[0].kind == "multiple_active_jpg"
    with pytest.raises(ValueError, match="review_state_invalid"):
        assert_review_state_valid(tmp_path)
