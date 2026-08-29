# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_series.py
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

from app.decision_contract import ManualKeepDecision, SeriesDecision, apply_manual_keep
from app.metadata_contract import build_keywords, write_and_readback
from app.phase1_manifest import build_manifest, write_manifest


def test_series_and_manual_keep_contracts():
    series = SeriesDecision("s1", 1, 2, True, None)
    series.validate()
    row = apply_manual_keep({}, ManualKeepDecision(True, "matched", .95))
    assert row["decision"] == "keep"
    assert row["decision_reason"] == "manual_keep_match"
    with pytest.raises(ValueError):
        ManualKeepDecision(True, None).validate()


def test_metadata_keywords_are_namespaced():
    keywords = build_keywords({"decision": "keep", "manual_keep": True,
                               "series_id": "s1", "series_rank": 1,
                               "series_best": True, "detected_people": ["alice"]})
    assert "workflow:ai_cull" in keywords
    assert "manual_keep:true" in keywords
    assert all(":" in keyword for keyword in keywords)


def test_manifest_contains_file_and_csv_hash(tmp_path: Path):
    (tmp_path / "image.jpg").write_bytes(b"image")
    (tmp_path / "scores.csv").write_text("file,score\nimage.jpg,1\n")
    manifest = build_manifest("batch+12345678", tmp_path,
                              entries=[{"relative_path": "image.jpg"}],
                              csv_path=tmp_path / "scores.csv",
                              config_fingerprint="a" * 64,
                              producer_version="test", counters={"total": 1})
    output = tmp_path / "manifest.json"
    digest = write_manifest(output, manifest)
    saved = json.loads(output.read_text())
    assert saved["batch_id"] == "batch+12345678"
    assert saved["culling_scores_hash"]
    assert len(digest) == 64


def test_metadata_dry_run_has_no_write(tmp_path: Path):
    result = write_and_readback(tmp_path / "missing.jpg", {"decision": "keep",
        "star_rating": 5}, dry_run=True)
    assert result["status"] == "disabled"
    assert not (tmp_path / "missing.jpg").exists()