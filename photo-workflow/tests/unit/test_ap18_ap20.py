from __future__ import annotations

from pathlib import Path

from app.phase3_resume import CorrelationRecord, index_resolution_status, load_correlation, write_correlation
from app.phase3_transfer import transfer_batch
from app.synology_photos_adapter import SynologyPhotosAdapter


def config(root: Path) -> dict:
    return {"paths": {"base_dir": str(root / "base"),
                       "publish_root": str(root / "publish")}}


def test_dry_run_does_not_transfer(tmp_path: Path):
    source = tmp_path / "base" / "batch"
    source.mkdir(parents=True)
    (source / "image.jpg").write_bytes(b"image")
    result = transfer_batch(source, tmp_path / "publish" / "batch", config(tmp_path),
                            batch_id="b+12345678", dry_run=True)
    assert result["status"] == "planned"
    assert not (tmp_path / "publish" / "batch").exists()


def test_move_verifies_before_source_removal(tmp_path: Path):
    source = tmp_path / "base" / "batch"
    source.mkdir(parents=True)
    (source / "image.jpg").write_bytes(b"image")
    result = transfer_batch(source, tmp_path / "publish" / "batch", config(tmp_path),
                            batch_id="b+12345678", mode="move")
    assert result["status"] == "transferred"
    assert not source.exists()
    assert (tmp_path / "publish" / "batch" / "image.jpg").exists()


def test_synology_defaults_to_dry_run(tmp_path: Path):
    adapter = SynologyPhotosAdapter({"synology_api": {"enabled": True}})
    assert adapter.healthcheck().status == "dry_run"
    assert adapter.apply_metadata(relative_path="image.jpg", rating=5, tags=[])["status"] == "capability_unsupported"


def test_correlation_record_is_resumeable(tmp_path: Path):
    path = tmp_path / "correlation.json"
    write_correlation(path, CorrelationRecord("image.jpg", attempt_count=1))
    loaded = load_correlation(path)
    assert loaded.relative_path == "image.jpg"
    assert index_resolution_status(10, 10) == "timeout"
