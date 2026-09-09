# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_face_proposal_duplicates.py
# PURPOSE:     Tests fuer Dubletten-Erkennung und Qualitaetsersatz (P4).
# AUTHOR:      Matzethias
# DATE:        2026-09-09
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+, pytest, Pillow
# CHANGES:
#   2026-09-09 | 1.0.0 | P4: Initiale Tests zum Dubletten-Contract.
# =============================================================================


from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.faces.face_proposal_batch import (
    build_face_proposal_batch,
    build_stable_crop_filename,
)
from app.faces.face_proposal_registration import register_face_proposals
from app.faces.proposal_contract import FaceProposalError, add_face_proposal

LIMITS = {"max_new": 20, "max_new_per_batch": 5}
BOX = {"left": 8, "top": 8, "right": 40, "bottom": 40}
SOURCE_ID = "batch7:IMG_0001.jpg:face-0"


def _pool(tmp_path: Path) -> Path:
    """Legt einen leeren Personen-Pool mit new_faces an."""
    pool = tmp_path / "faces" / "opa"
    (pool / "new_faces").mkdir(parents=True, exist_ok=True)
    return pool


def _add(pool: Path, source_id: str, quality: float, crop_name: str = "seed.jpg"):
    """Registriert einen Vorschlag direkt ueber den Contract."""
    return add_face_proposal(
        pool_root=pool,
        slug="opa",
        source_id=source_id,
        batch_id="batch7",
        crop_path=pool / "new_faces" / crop_name,
        original_path="orig.jpg",
        quality_score=quality,
        candidate_utility_score=quality,
        bounding_box=dict(BOX),
        face_confidence=0.9,
        limits=dict(LIMITS),
    )


def _read_images(pool: Path) -> list[dict]:
    """Liest die images-Liste der selection.json."""
    raw = (pool / "selection.json").read_text(encoding="utf-8")
    return json.loads(raw)["images"]


def _write_active(pool: Path, source_id: str) -> None:
    """Schreibt eine selection.json mit einem aktiven Referenzeintrag."""
    payload = {
        "schema_version": 1,
        "pool_type": "face",
        "slug": "opa",
        "images": [{
            "source_id": source_id,
            "path": "reference/opa_1.jpg",
            "status": "active",
            "quality_score": 0.9,
        }],
    }
    (pool / "selection.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_worse_duplicate_is_rejected_and_keeps_entry(tmp_path: Path) -> None:
    """Schlechtere Dublette: Eintrag und Pfad bleiben unberuehrt."""
    pool = _pool(tmp_path)
    _add(pool, SOURCE_ID, 1.0)
    with pytest.raises(FaceProposalError):
        _add(pool, SOURCE_ID, 0.5, crop_name="new.jpg")
    images = _read_images(pool)
    assert len(images) == 1
    assert images[0]["quality_score"] == 1.0
    assert images[0]["path"] == "new_faces/seed.jpg"


def test_better_or_equal_duplicate_replaces_entry(tmp_path: Path) -> None:
    """Bessere und gleich gute Dublette ersetzen genau einen Eintrag."""
    pool = _pool(tmp_path)
    _add(pool, SOURCE_ID, 0.0)
    _add(pool, SOURCE_ID, 0.5, crop_name="new.jpg")
    _add(pool, SOURCE_ID, 0.5, crop_name="new2.jpg")
    images = _read_images(pool)
    assert len(images) == 1
    assert images[0]["quality_score"] == 0.5
    assert images[0]["path"] == "new_faces/new2.jpg"


def test_active_source_blocks_new_proposal(tmp_path: Path) -> None:
    """Aktive Referenz mit gleicher Quelle blockiert jeden Vorschlag."""
    pool = _pool(tmp_path)
    _write_active(pool, SOURCE_ID)
    with pytest.raises(FaceProposalError):
        _add(pool, SOURCE_ID, 0.99)
    assert len(_read_images(pool)) == 1


def _image(path: Path) -> Path:
    """Schreibt ein kleines echtes JPEG als Crop-Quelle."""
    from PIL import Image

    Image.new("RGB", (64, 64), (128, 64, 32)).save(path, format="JPEG")
    return path


def _row(
    batch: str,
    source_id: str,
    image: Path,
    *,
    confidence: float = 0.9,
    area: float = 0.2,
    sharpness: float = 0.8,
    exposure: float = 0.8,
    framing: float = 0.8,
) -> dict:
    """Baut eine produktionsnahe Row mit steuerbaren Qualitaetsfeldern."""
    return {
        "batch_id": batch,
        "source_id": source_id,
        "person_slug": "opa",
        "known_person": True,
        "original_path": str(image),
        "bounding_box": dict(BOX),
        "face_confidence": confidence,
        "face_area_ratio": area,
        "sharpness_score": sharpness,
        "exposure_score": exposure,
        "framing_score": framing,
    }


def _run(rows: list[dict], tmp_path: Path) -> dict:
    """Startet den Batch gegen den Test-Pool."""
    return build_face_proposal_batch(
        rows,
        batch_id="batch7",
        output_root=tmp_path / "faces",
        min_quality_score=0.0,
    )


def test_batch_skips_worse_duplicate_and_keeps_file(tmp_path: Path) -> None:
    """Schlechtere Dublette: Datei und Eintrag bleiben erhalten."""
    image = _image(tmp_path / "IMG_0001.jpg")
    pool = _pool(tmp_path)
    name = build_stable_crop_filename("batch7", SOURCE_ID)
    target = pool / "new_faces" / name
    target.write_bytes(b"original-bytes")
    _add(pool, SOURCE_ID, 1.0, crop_name=name)

    weak_row = _row(
        "batch7", SOURCE_ID, image,
        confidence=0.5, area=0.05, sharpness=0.2, exposure=0.2, framing=0.2,
    )
    result = _run([weak_row], tmp_path)
    assert result["counters"]["created_new"] == 0
    assert result["counters"]["skipped_existing_better"] == 1
    assert target.read_bytes() == b"original-bytes"
    assert len(_read_images(pool)) == 1


def test_batch_replaces_better_duplicate(tmp_path: Path) -> None:
    """Bessere Dublette ersetzt Datei und aktualisiert genau einen Eintrag."""
    image = _image(tmp_path / "IMG_0001.jpg")
    pool = _pool(tmp_path)
    name = build_stable_crop_filename("batch7", SOURCE_ID)
    target = pool / "new_faces" / name
    target.write_bytes(b"original-bytes")
    _add(pool, SOURCE_ID, 0.0, crop_name=name)

    result = _run([_row("batch7", SOURCE_ID, image)], tmp_path)
    assert result["counters"]["created_new"] == 1
    assert result["counters"]["replaced_existing"] == 1
    assert target.read_bytes() != b"original-bytes"

    registration = register_face_proposals(
        result["candidates"],
        pool_root=tmp_path / "faces",
        limits=dict(LIMITS),
    )
    assert registration["registered_count"] == 1
    images = _read_images(pool)
    assert len(images) == 1
    assert images[0]["quality_score"] == result["candidates"][0]["quality_score"]


def test_batch_skips_active_source(tmp_path: Path) -> None:
    """Aktive Referenz: kein neuer Crop, kein neuer Eintrag."""
    image = _image(tmp_path / "IMG_0001.jpg")
    pool = _pool(tmp_path)
    _write_active(pool, SOURCE_ID)

    result = _run([_row("batch7", SOURCE_ID, image)], tmp_path)
    assert result["counters"]["skipped_existing_active"] == 1
    assert result["counters"]["created_new"] == 0
    name = build_stable_crop_filename("batch7", SOURCE_ID)
    assert not (pool / "new_faces" / name).exists()


def test_rerun_batch_stays_single_entry(tmp_path: Path) -> None:
    """Wiederholungsbatch: gleiche Quelle fuehrt zu genau einem Eintrag."""
    image = _image(tmp_path / "IMG_0001.jpg")
    rows = [_row("batch7", SOURCE_ID, image)]

    first = _run(rows, tmp_path)
    assert first["counters"]["created_new"] == 1
    register_face_proposals(
        first["candidates"], pool_root=tmp_path / "faces", limits=dict(LIMITS)
    )

    second = _run(rows, tmp_path)
    assert second["counters"]["created_new"] == 1
    assert second["counters"]["replaced_existing"] == 1
    register_face_proposals(
        second["candidates"], pool_root=tmp_path / "faces", limits=dict(LIMITS)
    )

    assert len(_read_images(tmp_path / "faces" / "opa")) == 1
