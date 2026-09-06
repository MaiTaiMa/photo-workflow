# -*- coding: utf-8 -*-
"""Tests fuer build_learning_status in photo_workflow."""
import json
from pathlib import Path

from app.photo_workflow import AUTO_LEARN_EXPORTED, build_learning_status


def _cfg(tmp_path: Path) -> dict:
    return {
        "personal_scoring": {"enabled": True},
        "training": {"sample_images_dir": str(tmp_path / "ref")},
        "paths": {"personal_model": str(tmp_path / "model.json")},
    }


def test_learning_status_without_config_fails_soft():
    AUTO_LEARN_EXPORTED.clear()
    status = build_learning_status({})
    assert status["exported_this_run"] == 0
    assert status["model_status"] == "unavailable"


def test_learning_status_reads_meta_no_pending(tmp_path):
    from app.training import build_personal_reference_state
    (tmp_path / "ref").mkdir()
    cfg = _cfg(tmp_path)
    state = build_personal_reference_state(cfg)
    (tmp_path / "personal_model_meta.json").write_text(
        json.dumps({
            "status": "cache_used",
            "source_image_count": 0,
            "reference_state": state,
        }),
        encoding="utf-8",
    )
    AUTO_LEARN_EXPORTED.clear()
    AUTO_LEARN_EXPORTED.append(("batch-1", 2))
    status = build_learning_status(cfg)
    assert status["enabled"] is True
    assert status["exported_this_run"] == 2
    assert status["exported_batches"] == ["batch-1"]
    assert status["model_status"] == "cache_used"
    assert status["rebuild_pending"] is False
    AUTO_LEARN_EXPORTED.clear()


def test_learning_status_detects_pending_rebuild(tmp_path):
    from app.training import build_personal_reference_state
    (tmp_path / "ref").mkdir()
    cfg = _cfg(tmp_path)
    state = build_personal_reference_state(cfg)
    (tmp_path / "personal_model_meta.json").write_text(
        json.dumps({
            "status": "cache_used",
            "source_image_count": 0,
            "reference_state": state,
        }),
        encoding="utf-8",
    )
    (tmp_path / "ref" / "neu.jpg").write_bytes(b"x")
    AUTO_LEARN_EXPORTED.clear()
    status = build_learning_status(cfg)
    assert status["rebuild_pending"] is True
