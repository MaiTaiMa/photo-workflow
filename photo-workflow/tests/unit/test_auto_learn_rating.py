# -*- coding: utf-8 -*-
"""Tests fuer das Keep-Rating-Sidecar beim Auto-Learn-Export."""
from pathlib import Path

from app.metadata_rating import read_rating
from app.training import KEEP_EXPORT_RATING, export_keep_samples


def _cfg(tmp_path: Path) -> dict:
    target = tmp_path / "training" / "reference"
    return {
        "personal_scoring": {"enabled": True, "source_dir": str(target)},
        "training": {"sample_images_dir": str(target)},
        "paths": {"personal_model": str(tmp_path / "model.json")},
    }


def _workdir_with_keep(tmp_path: Path):
    workdir = tmp_path / "batch-9"
    workdir.mkdir()
    (workdir / "keep1.JPG").write_bytes(b"keep-image")
    return workdir, [{"decision": "keep", "final_path": "keep1.JPG"}]


def test_export_writes_rating_sidecar(tmp_path):
    workdir, rows = _workdir_with_keep(tmp_path)
    result = export_keep_samples(rows, workdir, _cfg(tmp_path))
    assert result["exported"] == 1
    sidecar = tmp_path / "training" / "reference" / "batch-9__keep1.JPG.xmp"
    assert sidecar.is_file()


def test_exported_keep_reads_keep_rating(tmp_path):
    workdir, rows = _workdir_with_keep(tmp_path)
    export_keep_samples(rows, workdir, _cfg(tmp_path))
    exported = tmp_path / "training" / "reference" / "batch-9__keep1.JPG"
    assert read_rating(exported) == KEEP_EXPORT_RATING


def test_original_file_gets_no_sidecar(tmp_path):
    workdir, rows = _workdir_with_keep(tmp_path)
    export_keep_samples(rows, workdir, _cfg(tmp_path))
    assert not (workdir / "keep1.JPG.xmp").exists()
    assert not (workdir / "keep1.xmp").exists()
