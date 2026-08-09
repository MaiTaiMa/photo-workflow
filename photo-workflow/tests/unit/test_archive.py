from __future__ import annotations

from pathlib import Path

import pytest

from app.archive_contract import ArchiveError, create_verified_zip
from app.recovery import quarantine_batch
from app.review_contract import ReviewRecordError, write_review_record


def test_review_record_is_immutable(tmp_path: Path):
    target = tmp_path / "review_decision_record.json"
    digest = write_review_record(target, batch_id="b+12345678",
        human_decision="keep", predicted_decision="keep",
        config_fingerprint="a" * 64, producer_version="test", image_count=1)
    assert len(digest) == 64
    with pytest.raises(ReviewRecordError):
        write_review_record(target, batch_id="b+12345678",
            human_decision="reject", predicted_decision="keep",
            config_fingerprint="a" * 64, producer_version="test", image_count=1)


def test_archive_is_verified_and_collision_safe(tmp_path: Path):
    (tmp_path / "image.jpg").write_bytes(b"image")
    first = create_verified_zip(tmp_path, tmp_path / "batch.zip", ["image.jpg"],
        batch_id="b+12345678", config_fingerprint="a" * 64, producer_version="test")
    second = create_verified_zip(tmp_path, tmp_path / "batch.zip", ["image.jpg"],
        batch_id="b+12345678", config_fingerprint="a" * 64, producer_version="test")
    assert first["entry_count"] == 1
    assert second["archive_path"].endswith("_EXTRA2.zip")


def test_archive_rejects_traversal(tmp_path: Path):
    (tmp_path / "image.jpg").write_bytes(b"image")
    with pytest.raises(ArchiveError):
        create_verified_zip(tmp_path, tmp_path / "batch.zip", ["../image.jpg"],
            batch_id="b+12345678", config_fingerprint="a" * 64, producer_version="test")


def test_quarantine_preserves_source(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "original.arw").write_bytes(b"raw")
    destination = quarantine_batch(source, tmp_path / "quarantine",
                                   reason="review_state_invalid", batch_id="b+12345678")
    assert (source / "original.arw").exists()
    assert (destination / "original.arw").exists()
    assert "review_state_invalid" in (destination / "QUARANTINE_REASON.txt").read_text()
