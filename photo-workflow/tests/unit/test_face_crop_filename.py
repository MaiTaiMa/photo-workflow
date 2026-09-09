# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_face_crop_filename.py
# PURPOSE:     Tests fuer stabile, sichere Face-Crop-Dateinamen (P3).
# AUTHOR:      Matzethias
# DATE:        2026-09-09
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+, pytest, Pillow
# CHANGES:
#   2026-09-09 | 1.0.0 | P3: Initiale Tests zum stabilen Namenscontract.
# =============================================================================


from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.faces.face_proposal_batch import (
    FaceProposalBatchError,
    build_face_proposal_batch,
    build_stable_crop_filename,
)

# === Namenscontract ===
# Erlaubte Zeichen und verbindliches Grundformat des Crop-Dateinamens.
SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+__face-[0-9]{3}\.jpg$")


def test_same_source_key_yields_same_name() -> None:
    """Gleiche Quellenkennung erzeugt immer denselben Dateinamen."""
    first = build_stable_crop_filename("batch7", "batch7:IMG_0001.jpg:face-0")
    second = build_stable_crop_filename("batch7", "batch7:IMG_0001.jpg:face-0")
    assert first == second
    assert first == "batch7__batch7-IMG_0001__face-000.jpg"


def test_face_index_comes_from_source_id_suffix() -> None:
    """Der Index stammt aus ':face-N', nicht aus dem fehlenden Row-Feld."""
    name = build_stable_crop_filename("b", "b:IMG.jpg:face-12")
    assert name.endswith("__face-012.jpg")


def test_distinct_faces_get_distinct_names() -> None:
    """Zwei Gesichter im selben Bild erzeugen keine Namenskollision mehr."""
    first = build_stable_crop_filename("b", "b:IMG.jpg:face-0")
    second = build_stable_crop_filename("b", "b:IMG.jpg:face-1")
    assert first != second


def test_explicit_face_index_wins_over_source_suffix() -> None:
    """Ein gesetztes Row-Feld hat Vorrang vor dem Suffix."""
    name = build_stable_crop_filename("b", "b:IMG.jpg:face-1", 3)
    assert name.endswith("__face-003.jpg")


def test_unsafe_characters_are_replaced() -> None:
    """Doppelpunkt, Leerzeichen und Umlaute werden sicher ersetzt."""
    name = build_stable_crop_filename(
        "Mein Batch", "Mein Batch:Übung 1.jpg:face-0"
    )
    assert SAFE_NAME.match(name)
    assert ":" not in name and " " not in name and "/" not in name


def test_dotdot_batch_id_is_rejected() -> None:
    """Ein reines '..' als batch_id wird nicht zum Dateinamen."""
    with pytest.raises(FaceProposalBatchError):
        build_stable_crop_filename("..", "b:IMG.jpg:face-0")


def test_separators_are_neutralized() -> None:
    """Separatoren in der Quellenkennung erzeugen keinen Pfad."""
    name = build_stable_crop_filename("b", "a/b:IMG.jpg:face-0")
    assert SAFE_NAME.match(name)
    assert Path(name).name == name


def test_invalid_face_index_is_rejected() -> None:
    """Boolesche und negative Indizes blockieren den Vorschlag."""
    with pytest.raises(FaceProposalBatchError):
        build_stable_crop_filename("b", "b:IMG.jpg:face-0", True)
    with pytest.raises(FaceProposalBatchError):
        build_stable_crop_filename("b", "b:IMG.jpg:face-0", -1)


def _make_image(path: Path, size: int = 64) -> Path:
    """Schreibt ein kleines echtes JPEG als Crop-Quelle."""
    from PIL import Image

    Image.new("RGB", (size, size), (128, 64, 32)).save(path, format="JPEG")
    return path


def _row(batch: str, index: int, image: Path) -> dict:
    """Baut eine produktionsnahe Row mit echten Qualitaetsfeldern."""
    return {
        "batch_id": batch,
        "source_id": f"{batch}:IMG_0001.jpg:face-{index}",
        "person_slug": "opa",
        "known_person": True,
        "original_path": str(image),
        "bounding_box": {"left": 8, "top": 8, "right": 40, "bottom": 40},
        "face_confidence": 0.9,
        "face_area_ratio": 0.2,
        "sharpness_score": 0.8,
        "exposure_score": 0.8,
        "framing_score": 0.8,
    }


def test_batch_creates_distinct_stable_crops(tmp_path: Path) -> None:
    """End-to-end: Zwei Gesichter, ein Bild, zwei stabile Crop-Dateien."""
    image = _make_image(tmp_path / "IMG_0001.jpg")
    rows = [_row("batch7", 0, image), _row("batch7", 1, image)]
    result = build_face_proposal_batch(
        rows,
        batch_id="batch7",
        output_root=tmp_path / "faces",
        min_quality_score=0.0,
    )
    paths = [candidate["path"] for candidate in result["candidates"]]
    assert paths == [
        "new_faces/batch7__batch7-IMG_0001__face-000.jpg",
        "new_faces/batch7__batch7-IMG_0001__face-001.jpg",
    ]
    assert result["counters"]["created_new"] == 2
    for candidate in result["candidates"]:
        assert Path(candidate["crop_path"]).is_file()

    rerun = build_face_proposal_batch(
        rows,
        batch_id="batch7",
        output_root=tmp_path / "faces",
        min_quality_score=0.0,
    )
    assert [c["path"] for c in rerun["candidates"]] == paths
