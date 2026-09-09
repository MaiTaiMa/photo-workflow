# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_face_proposal_diversity.py
# PURPOSE:     Tests fuer die optionale Embedding-Diversitaet (P5).
# AUTHOR:      Matzethias
# DATE:        2026-09-09
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+, pytest
# CHANGES:
#   2026-09-09 | 1.0.0 | P5: Initiale Tests mit Fake-Embedder.
# =============================================================================


from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.faces.face_proposal_registration import register_face_proposals
from app.faces.face_proposal_selection import (
    FaceCandidateSelectionError,
    diversify_face_candidates,
)

BOX = {"left": 8, "top": 8, "right": 40, "bottom": 40}
LIMITS = {"max_new": 20, "max_new_per_batch": 5}


def _candidate(source_id: str, crop_path: str, **extra) -> dict:
    """Baut einen minimalen Kandidaten mit Registrierungsfeldern."""
    candidate = {
        "source_id": source_id,
        "batch_id": "batch7",
        "person_slug": "opa",
        "crop_path": crop_path,
        "original_path": "orig.jpg",
        "quality_score": 0.9,
        "candidate_utility_score": 0.9,
        "bounding_box": dict(BOX),
        "face_confidence": 0.9,
    }
    candidate.update(extra)
    return candidate


def _embedder(vectors: dict[str, list[float]]):
    """Fake-Embedder: bildet Pfade auf feste Vektoren ab."""
    return lambda path: vectors.get(path)


def test_similar_candidates_are_dropped() -> None:
    """Zwei fast gleiche Vektoren: der zweite wird verworfen."""
    candidates = [
        _candidate("s1", "a.jpg"),
        _candidate("s2", "b.jpg"),
    ]
    kept, dropped, info = diversify_face_candidates(
        candidates,
        min_candidate_distance=0.1,
        embedder=_embedder({"a.jpg": [1.0, 0.0], "b.jpg": [0.99, 0.01]}),
    )
    assert [c["source_id"] for c in kept] == ["s1"]
    assert [c["source_id"] for c in dropped] == ["s2"]
    assert info == {"embedded": 2, "no_embedding": 0, "dropped": 1}


def test_diverse_candidates_are_kept() -> None:
    """Grosser Abstand: beide Kandidaten bleiben erhalten."""
    candidates = [
        _candidate("s1", "a.jpg"),
        _candidate("s2", "b.jpg"),
    ]
    kept, dropped, info = diversify_face_candidates(
        candidates,
        min_candidate_distance=0.5,
        embedder=_embedder({"a.jpg": [1.0, 0.0], "b.jpg": [0.0, 1.0]}),
    )
    assert [c["source_id"] for c in kept] == ["s1", "s2"]
    assert info["dropped"] == 0


def test_missing_embedding_falls_back_to_keep() -> None:
    """Embedder ohne Ergebnis: Kandidat wird wie bisher akzeptiert."""
    candidates = [_candidate("s1", "a.jpg")]
    kept, dropped, info = diversify_face_candidates(
        candidates,
        min_candidate_distance=0.5,
        embedder=_embedder({}),
    )
    assert len(kept) == 1
    assert info["no_embedding"] == 1
    assert "embedding" not in kept[0]


def test_existing_embedding_is_reused() -> None:
    """Ein vorhandener Vektor loest keinen weiteren Embedder-Aufruf aus."""
    calls: list[str] = []

    def recording_embedder(path: str):
        calls.append(path)
        return [0.0, 1.0]

    candidates = [
        _candidate("s1", "a.jpg", embedding=[1.0, 0.0]),
        _candidate("s2", "b.jpg"),
    ]
    kept, _dropped, _info = diversify_face_candidates(
        candidates,
        min_candidate_distance=0.5,
        embedder=recording_embedder,
    )
    assert len(kept) == 2
    assert calls == ["b.jpg"]


def test_invalid_arguments_are_rejected() -> None:
    """Unzulaessige Schwellwerte und Embedder blockieren."""
    with pytest.raises(FaceCandidateSelectionError):
        diversify_face_candidates(
            [], min_candidate_distance=2.5, embedder=_embedder({})
        )
    with pytest.raises(FaceCandidateSelectionError):
        diversify_face_candidates(
            [], min_candidate_distance=0.5, embedder="kein-callable"
        )


def test_embedding_is_never_persisted(tmp_path: Path) -> None:
    """Nach der Registrierung enthaelt selection.json keine Vektoren."""
    pool_root = tmp_path / "faces"
    person_dir = pool_root / "opa" / "new_faces"
    person_dir.mkdir(parents=True)
    candidates = [
        _candidate("s1", str(person_dir / "a.jpg")),
        _candidate("s2", str(person_dir / "b.jpg")),
    ]
    kept, _dropped, _info = diversify_face_candidates(
        candidates,
        min_candidate_distance=0.5,
        embedder=_embedder({
            str(person_dir / "a.jpg"): [1.0, 0.0],
            str(person_dir / "b.jpg"): [0.0, 1.0],
        }),
    )
    result = register_face_proposals(
        kept, pool_root=pool_root, limits=dict(LIMITS)
    )
    assert result["registered_count"] == 2
    raw = (pool_root / "opa" / "selection.json").read_text(encoding="utf-8")
    assert '"embedding"' not in raw
    assert len(json.loads(raw)["images"]) == 2
