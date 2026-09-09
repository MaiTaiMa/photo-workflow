# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/faces/face_proposal_batch.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-09-03
# VERSION:     1.2.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   2026-09-03 | 1.0.0 | P8.3: confidence_margin-Parameter hinzugefuegt.
#   2026-09-09 | 1.1.0 | P3: Stabile Crop-Dateinamen aus source_id.
#   2026-09-09 | 1.2.0 | P4: Dubletten-Erkennung gegen selection.json.
# =============================================================================


from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.faces.face_crop_generator import create_square_face_crop
from app.faces.face_proposal_scoring import (
    calculate_candidate_utility_score,
    calculate_quality_score,
)
from app.faces.proposal_contract import load_proposal_quality_index


def resolve_person_pool_dir(root, person_slug):
    """Bestehenden Personen-Ordner case-insensitiv aufloesen.

    Verhindert doppelte Ordner (z. B. 'Nelly' vs. 'nelly') auf
    case-sensitiven Dateisystemen. Faellt auf den Slug zurueck,
    wenn noch kein Ordner existiert.
    """
    base = Path(root)
    slug_fold = str(person_slug).casefold()
    if base.is_dir():
        for child in sorted(base.iterdir()):
            if child.is_dir() and child.name.casefold() == slug_fold:
                return child
    return base / str(person_slug)


class FaceProposalBatchError(ValueError):
    """Beschreibt einen ungültigen Face-Vorschlagsbatch."""


# === Stabile Crop-Dateinamen (P3) ===
# Zweck: Leitet den Dateinamen aus der stabilen Quellenkennung ab.
# Eingabe: batch_id, source_id ("batch:datei:face-N"), optionaler Index.
# Ausgabe: Sicherer Name "{batch}__{stem}__face-{NNN}.jpg" ohne Separatoren.

_UNSAFE_NAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")
_FACE_INDEX_MARKER = ":face-"


def _sanitize_name_part(value: object, field: str) -> str:
    """Ersetzt unsichere Zeichen und blockiert leere Namensbestandteile.

    Erlaubt sind nur A-Z, a-z, 0-9 sowie Punkt, Unter- und Bindestrich.
    Alle anderen Zeichen (inklusive Separatoren und Doppelpunkt) werden
    zu einem Bindestrich; ein leeres Ergebnis blockiert den Vorschlag.
    """
    cleaned = _UNSAFE_NAME_CHARS.sub("-", str(value)).strip("-.")
    if not cleaned:
        raise FaceProposalBatchError(f"{field} yields no safe filename part")
    return cleaned


def _face_index_from_source_id(source_id: str) -> int | None:
    """Liest den Face-Index aus dem ':face-N'-Suffix der Quellenkennung.

    Das produktive Format ist 'batch:datei:face-N' (photo_workflow.py).
    Fehlt das Suffix oder ist N keine Zahl, wird None geliefert.
    """
    if _FACE_INDEX_MARKER not in source_id:
        return None
    tail = source_id.rsplit(_FACE_INDEX_MARKER, 1)[1]
    try:
        return int(tail)
    except ValueError:
        return None


def build_stable_crop_filename(
    batch_id: str,
    source_id: str,
    face_index: object = None,
) -> str:
    """Erzeugt einen stabilen, sicheren Crop-Dateinamen.

    Gleiche Quellenkennung ergibt immer denselben Namen. Der Index kommt
    bevorzugt aus dem Row-Feld, sonst aus dem source_id-Suffix, sonst 0.
    """
    index = face_index
    if index is None:
        index = _face_index_from_source_id(source_id)
    if index is None:
        index = 0
    if isinstance(index, bool):
        raise FaceProposalBatchError("face_index must be an integer")
    try:
        index = int(index)
    except (TypeError, ValueError) as exc:
        raise FaceProposalBatchError("face_index must be an integer") from exc
    if index < 0:
        raise FaceProposalBatchError("face_index must be non-negative")

    batch_part = _sanitize_name_part(batch_id, "batch_id")
    stem_part = _sanitize_name_part(Path(str(source_id)).stem, "source_id")
    filename = f"{batch_part}__{stem_part}__face-{index:03d}.jpg"
    # Traversal-Schutz: Der fertige Name darf kein zusammengesetzter Pfad sein.
    if Path(filename).name != filename:
        raise FaceProposalBatchError("unsafe crop filename")
    return filename


def build_face_proposal_batch(
    rows: list[Mapping[str, Any]],
    *,
    batch_id: str,
    output_root: str | Path,
    min_quality_score: float = 0.65,
    confidence_margin: float = 0.1,
    limits: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Create only eligible known-face crops under ``new_faces``.

    Integration boundary: no reference activation and no selection.json
    writes happen here. The existing selection is read only to detect a
    duplicate stable source: worse duplicates are skipped, better or equal
    ones replace file and entry. Human activation is represented by moving
    a crop from new_faces to reference in a later workflow step.
    """
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise FaceProposalBatchError("batch_id must be a non-empty string")
    if not 0.0 <= float(min_quality_score) <= 1.0:
        raise FaceProposalBatchError("min_quality_score must be between 0 and 1")
    if not 0.0 <= float(confidence_margin) <= 1.0:
        raise FaceProposalBatchError("confidence_margin must be between 0 and 1")

    root = Path(output_root)
    created: list[dict[str, Any]] = []
    counters = {
        "known_matches": 0,
        "eligible_candidates": 0,
        "created_new": 0,
        "skipped_unknown": 0,
        "skipped_ambiguous": 0,
        "skipped_quality": 0,
        "skipped_limits": 0,
        "replaced_existing": 0,
        "skipped_existing_better": 0,
        "skipped_existing_active": 0,
    }
    created_per_person: dict[str, int] = {}
    quality_indexes: dict[str, dict[str, dict[str, object]]] = {}
    people: set[str] = set()

    for row in rows:
        if not isinstance(row, Mapping):
            raise FaceProposalBatchError("analysis row must be a mapping")
        if row.get("batch_id", batch_id) != batch_id:
            raise FaceProposalBatchError("analysis row batch_id mismatch")
        if row.get("known_person") is not True:
            counters["skipped_unknown"] += 1
            continue
        if row.get("ambiguous") is True:
            counters["skipped_ambiguous"] += 1
            continue

        person_slug = row.get("person_slug")
        image_path = row.get("original_path")
        box = row.get("bounding_box")
        confidence = row.get("face_confidence")
        if not isinstance(person_slug, str) or not person_slug.strip():
            counters["skipped_unknown"] += 1
            continue
        counters["known_matches"] += 1
        people.add(person_slug)

        quality = calculate_quality_score(
            face_confidence=confidence,
            face_area_ratio=row.get("face_area_ratio"),
            sharpness_score=row.get("sharpness_score"),
            exposure_score=row.get("exposure_score"),
            framing_score=row.get("framing_score"),
        )
        if quality < min_quality_score:
            counters["skipped_quality"] += 1
            continue

        counters["eligible_candidates"] += 1
        utility = calculate_candidate_utility_score(
            quality_score=quality,
            diversity_score=row.get("diversity_score", 0.5),
            robustness_score=row.get("robustness_score", 0.5),
            confidence_score=confidence,
        )
        source_id = row.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            raise FaceProposalBatchError("eligible candidate source_id is missing")
        # Dubletten-Check gegen den bestehenden Pool (read-only).
        person_index = quality_indexes.get(person_slug)
        if person_index is None:
            person_index = load_proposal_quality_index(
                resolve_person_pool_dir(root, person_slug), person_slug
            )
            quality_indexes[person_slug] = person_index
        existing = person_index.get(source_id)
        if existing is not None:
            if existing["status"] != "new":
                counters["skipped_existing_active"] += 1
                continue
            if float(existing["quality_score"]) > quality:
                counters["skipped_existing_better"] += 1
                continue
            counters["replaced_existing"] += 1
        filename = build_stable_crop_filename(
            batch_id,
            source_id,
            row.get("face_index"),
        )
        # Limits vor Crop-Erzeugung
        if limits:
            _max_batch = int(limits.get("max_new_per_batch") or 0)
            _max_total = int(limits.get("max_new") or 0)
            if (_max_batch and created_per_person.get(person_slug, 0) >= _max_batch) or (
                _max_total and counters["created_new"] >= _max_total
            ):
                counters["skipped_limits"] += 1
                continue
        created_per_person[person_slug] = created_per_person.get(person_slug, 0) + 1

        crop_path = resolve_person_pool_dir(root, person_slug) / "new_faces" / filename
        create_square_face_crop(image_path, box, crop_path)
        created.append({
            "source_id": source_id,
            "batch_id": batch_id,
            "person_slug": person_slug,
            "path": f"new_faces/{filename}",
            "crop_path": str(crop_path),
            "original_path": str(image_path),
            "quality_score": quality,
            "candidate_utility_score": utility,
            "bounding_box": dict(box),
            "face_confidence": float(confidence),
            "status": "new",
        })
        counters["created_new"] += 1

    counters["people_with_new_proposals"] = sorted({
        item["person_slug"] for item in created
    })
    return {"batch_id": batch_id, "candidates": created, "counters": counters}
