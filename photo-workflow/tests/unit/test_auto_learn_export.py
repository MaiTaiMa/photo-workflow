# -*- coding: utf-8 -*-
"""Tests fuer den automatischen Keep-Export (Auto-Learn) am Batch-Ende."""
from pathlib import Path

from app.training import export_keep_samples


def _cfg(tmp_path: Path, enabled: bool = True) -> dict:
    target = tmp_path / "training" / "reference"
    return {
        "personal_scoring": {"enabled": enabled, "source_dir": str(target)},
        "training": {"sample_images_dir": str(target)},
        "paths": {"personal_model": str(tmp_path / "model.json")},
    }


def _rows_and_workdir(tmp_path: Path):
    workdir = tmp_path / "batch-1"
    workdir.mkdir()
    (workdir / "keep1.JPG").write_bytes(b"keep-image")
    rejected = workdir / "Rejected"
    rejected.mkdir()
    (rejected / "reject1.JPG").write_bytes(b"reject-image")
    rows = [
        {"decision": "keep", "final_path": "keep1.JPG"},
        {"decision": "reject", "final_path": "Rejected/reject1.JPG"},
        {"decision": "review", "final_path": "Rejected/reject1.JPG"},
    ]
    return rows, workdir


def test_export_keep_samples_copies_only_keeps(tmp_path):
    rows, workdir = _rows_and_workdir(tmp_path)
    result = export_keep_samples(rows, workdir, _cfg(tmp_path))
    target = tmp_path / "training" / "reference" / "batch-1__keep1.JPG"
    assert result["exported"] == 1
    assert target.is_file()
    assert target.read_bytes() == b"keep-image"
    assert not (tmp_path / "training" / "reference" / "batch-1__reject1.JPG").exists()


def test_export_keep_samples_is_idempotent(tmp_path):
    rows, workdir = _rows_and_workdir(tmp_path)
    cfg = _cfg(tmp_path)
    first = export_keep_samples(rows, workdir, cfg)
    second = export_keep_samples(rows, workdir, cfg)
    assert first["exported"] == 1
    assert second["exported"] == 0
    assert second["skipped"] >= 1


def test_export_keep_samples_respects_disabled(tmp_path):
    rows, workdir = _rows_and_workdir(tmp_path)
    result = export_keep_samples(rows, workdir, _cfg(tmp_path, enabled=False))
    assert result["exported"] == 0
    assert not (tmp_path / "training" / "reference").exists()
