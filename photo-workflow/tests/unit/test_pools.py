# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_pools.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from app.faces.crop_contract import CropContractError, save_new_face_crop
from app.faces.pool_rebuild import PoolRebuildError, RuntimeReferenceCache, rebuild_pool


def test_pool_rebuild_ranks_active_images_without_embeddings(tmp_path: Path):
    payload = rebuild_pool(tmp_path / "faces" / "alice", pool_type="face", slug="alice",
        images=[{"path": "a.jpg", "status": "active", "pool_utility_score": .5},
                {"path": "b.jpg", "status": "active", "pool_utility_score": .9}],
        limits={"max_active": 3, "max_new": 2}, model_fingerprint="m1",
        preprocessing_fingerprint="p1")
    assert payload["images"][0]["path"] == "b.jpg"
    assert "embedding" not in json.dumps(payload)
    assert payload["images"][0]["pool_rank"] == 1


def test_pool_rebuild_enforces_max_active(tmp_path: Path):
    with pytest.raises(PoolRebuildError):
        rebuild_pool(tmp_path / "pool", pool_type="face", slug="x",
            images=[{"path": "a.jpg", "status": "active"},
                    {"path": "b.jpg", "status": "active"}],
            limits={"max_active": 1}, model_fingerprint="m", preprocessing_fingerprint="p")


def test_crop_is_written_only_to_new_faces(tmp_path: Path):
    source = tmp_path / "photo.jpg"
    Image.new("RGB", (20, 20), "white").save(source)
    target = save_new_face_crop(source, tmp_path / "faces", slug="alice",
                                filename="candidate.jpg",
                                box={"left": 1, "top": 1, "right": 10, "bottom": 10})
    assert target.parts[-2:] == ("new_faces", "candidate.jpg")
    with pytest.raises(CropContractError):
        save_new_face_crop(source, tmp_path / "faces", slug="alice",
                           filename="../bad.jpg", box={"left": 1, "top": 1, "right": 10, "bottom": 10})


def test_runtime_cache_rebuilds_after_fingerprint_change():
    cache = RuntimeReferenceCache()
    calls = []
    assert cache.get_or_rebuild("a", lambda: calls.append(1) or {"x": 1})["x"] == 1
    cache.get_or_rebuild("a", lambda: calls.append(1) or {"x": 2})
    cache.get_or_rebuild("b", lambda: calls.append(1) or {"x": 3})
    assert len(calls) == 2