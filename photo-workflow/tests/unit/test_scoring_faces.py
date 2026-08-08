from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.faces.matcher import FaceMatcher
from app.faces.protocol import BackendInfo
from app.faces.reference_pool import ReferencePoolError, load_active_references
from app.scoring.technical import score_image


class FakeBackend:
    info = BackendInfo("fake", "fake", "test", "cpu", "none", "cosine", "test")
    def embedding(self, image_path):
        name = Path(image_path).stem
        return np.array([1.0, 0.0] if "alice" in name else [0.0, 1.0])


def test_analysis_error_is_not_zero(tmp_path: Path):
    result = score_image(tmp_path / "missing.jpg")
    assert result.status == "analysis_error"
    assert result.base_score is None


def test_match_requires_margin():
    matcher = FaceMatcher(FakeBackend(), threshold=.2, margin=.05)
    matcher.add_reference("alice", "alice_ref.jpg")
    matcher.add_reference("bob", "bob_ref.jpg")
    result = matcher.match("alice_photo.jpg")
    assert result.status == "matched"
    assert result.person_slug == "alice"
    assert result.family_score is not None


def test_selection_rejects_embeddings(tmp_path: Path):
    root = tmp_path / "alice"
    (root / "reference").mkdir(parents=True)
    (root / "reference" / "ref.jpg").write_bytes(b"x")
    selection = {"schema_version": 1, "pool_type": "face", "slug": "alice",
                 "updated_at": "now", "selection_fingerprint": "bad",
                 "pool_build_id": "x", "rank_digits": 1, "limits": {},
                 "images": [{"status": "active", "path": "ref.jpg",
                             "embedding": [1, 2]}]}
    (root / "selection.json").write_text(json.dumps(selection))
    with pytest.raises(ReferencePoolError):
        load_active_references(root, pool_type="face", slug="alice")
