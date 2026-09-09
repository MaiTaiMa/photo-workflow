# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_face_not_used.py
# PURPOSE:     Tests fuer die not_used-Verschiebung und Berichtszeile (P6).
# AUTHOR:      Matzethias
# DATE:        2026-09-09
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+, pytest
# CHANGES:
#   2026-09-09 | 1.0.0 | P6: Initiale Tests zum not_used-Contract.
# =============================================================================


from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.faces.crop_contract import CropContractError, move_face_crop_to_not_used
from app.faces.face_proposal_reporting import format_registration_status_block


def _crop(tmp_path: Path, name: str = "x.jpg") -> Path:
    """Legt einen Crop unter <person>/new_faces an."""
    new_faces = tmp_path / "faces" / "Opa" / "new_faces"
    new_faces.mkdir(parents=True, exist_ok=True)
    crop = new_faces / name
    crop.write_bytes(b"crop-bytes")
    return crop


def test_move_happy_path(tmp_path: Path) -> None:
    """Crop landet unter not_used, Quelle ist weg, nichts ueberschrieben."""
    crop = _crop(tmp_path)
    target = move_face_crop_to_not_used(crop)
    assert target == tmp_path / "faces" / "Opa" / "not_used" / "x.jpg"
    assert target.read_bytes() == b"crop-bytes"
    assert not crop.exists()


def test_missing_source_is_rejected(tmp_path: Path) -> None:
    """Fehlende Quelldatei blockiert die Verschiebung."""
    missing = tmp_path / "faces" / "Opa" / "new_faces" / "ghost.jpg"
    with pytest.raises(CropContractError):
        move_face_crop_to_not_used(missing)


def test_existing_target_blocks_and_keeps_source(tmp_path: Path) -> None:
    """Belegtes Ziel blockiert; Quelle und Ziel bleiben unveraendert."""
    crop = _crop(tmp_path)
    target = tmp_path / "faces" / "Opa" / "not_used" / "x.jpg"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"alt")
    with pytest.raises(CropContractError):
        move_face_crop_to_not_used(crop)
    assert crop.read_bytes() == b"crop-bytes"
    assert target.read_bytes() == b"alt"


def test_wrong_parent_dir_is_rejected(tmp_path: Path) -> None:
    """Nur Crops direkt unter new_faces duerfen verschoben werden."""
    stray = tmp_path / "faces" / "Opa" / "reference" / "x.jpg"
    stray.parent.mkdir(parents=True)
    stray.write_bytes(b"crop-bytes")
    with pytest.raises(CropContractError):
        move_face_crop_to_not_used(stray)


def test_symlink_source_is_rejected(tmp_path: Path) -> None:
    """Symlinks werden aus Sicherheitsgruenden nicht verschoben."""
    real = _crop(tmp_path, name="real.jpg")
    link = real.parent / "link.jpg"
    os.symlink(real, link)
    with pytest.raises(CropContractError):
        move_face_crop_to_not_used(link)
    assert real.is_file()


def test_report_block_shows_not_used_per_person() -> None:
    """Der Statusblock enthaelt die Pro-Person-Zeile der Verschiebungen."""
    block = format_registration_status_block(
        batch_id="batch7",
        registration_result={"registered": [], "skipped_count": 0},
        not_used_moved_per_person={"Opa": 2},
    )
    assert "Nicht benötigt (verschoben)" in block
    assert "Opa: 2" in block
