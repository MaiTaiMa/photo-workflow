import json
from pathlib import Path

from app.phase3_transfer import transfer_batch


def _config(root: Path, mode: str = "copy") -> dict:
    return {
        "paths": {
            "base_dir": str(root / "base"),
            "publish_root": str(root / "publish"),
        },
        "finalization": {
            "enabled": True,
            "publish_to_synology_photos": {
                "enabled": True,
                "mode": mode,
                "indexing": {"enabled": False},
            },
        },
    }


def _source(root: Path) -> Path:
    source = root / "base" / "batch"
    source.mkdir(parents=True)
    (source / "photo.jpg").write_bytes(b"photo-data")
    return source


def test_copy_writes_valid_finalization_manifest(tmp_path: Path) -> None:
    source = _source(tmp_path)
    target = tmp_path / "publish" / "batch"

    result = transfer_batch(
        source,
        target,
        _config(tmp_path, "copy"),
        batch_id="batch-001",
        mode="copy",
    )

    manifest_path = target / "finalization_manifest.json"
    assert result["status"] == "transferred"
    assert source.exists()
    assert target.exists()
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["batch_id"] == "batch-001"
    assert manifest["status"] == "transferred"
    assert manifest["transfer_mode"] == "copy"
    assert manifest["files"][0]["relative_path"] == "photo.jpg"
    assert manifest["files"][0]["hash"]
    assert manifest["indexing"] is None  # Indexing war disabled


def test_move_removes_source_only_after_transfer(tmp_path: Path) -> None:
    source = _source(tmp_path)
    target = tmp_path / "publish" / "batch"

    result = transfer_batch(
        source,
        target,
        _config(tmp_path, "move"),
        batch_id="batch-002",
        mode="move",
    )

    assert result["status"] == "transferred"
    assert not source.exists()
    assert (target / "photo.jpg").read_bytes() == b"photo-data"
