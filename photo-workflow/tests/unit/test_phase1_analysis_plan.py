from __future__ import annotations

import json

import pytest

from app.phase1_analysis_plan import Phase1AnalysisPlanError, Phase1AnalysisPlanStore


def payload():
    return {
        "rows": [
            {"file": "IMG_0001.JPG", "decision": "keep", "manual_keep": False},
            {"file": "IMG_0002.JPG", "decision": "review", "manual_keep": True},
        ],
        "workunits": [
            {"workunit_id": "batch-a:wu-0001", "image_names": ["IMG_0001.JPG"]},
            {"workunit_id": "batch-a:wu-0002", "image_names": ["IMG_0002.JPG"]},
        ],
    }


def write_plan(tmp_path):
    store = Phase1AnalysisPlanStore(tmp_path, "test-v1")
    value = payload()
    record = store.write(batch_id="batch-a", rows=value["rows"], workunits=value["workunits"], config_fingerprint="config-hash")
    return store, record


def test_analysis_plan_round_trip_is_atomic_and_hash_valid(tmp_path) -> None:
    store, record = write_plan(tmp_path)
    assert store.load("batch-a") == record


def test_analysis_plan_rejects_hash_tampering(tmp_path) -> None:
    store, record = write_plan(tmp_path)
    record["rows"][0]["decision"] = "reject"
    store.path_for("batch-a").write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(Phase1AnalysisPlanError, match="hash"):
        store.load("batch-a")


def test_analysis_plan_rejects_internal_row_fields(tmp_path) -> None:
    store = Phase1AnalysisPlanStore(tmp_path, "test-v1")
    value = payload()
    value["rows"][0]["_source_path"] = "/private/path"
    with pytest.raises(Phase1AnalysisPlanError, match="forbidden"):
        store.write(batch_id="batch-a", config_fingerprint="config-hash", **value)


def test_analysis_plan_rejects_nested_embeddings(tmp_path) -> None:
    store = Phase1AnalysisPlanStore(tmp_path, "test-v1")
    value = payload()
    value["rows"][0]["details"] = {"embedding": [0.1, 0.2]}
    with pytest.raises(Phase1AnalysisPlanError, match="forbidden"):
        store.write(batch_id="batch-a", config_fingerprint="config-hash", **value)


def test_analysis_plan_requires_exact_workunit_image_membership(tmp_path) -> None:
    store = Phase1AnalysisPlanStore(tmp_path, "test-v1")
    value = payload()
    value["workunits"][1]["image_names"] = ["IMG_9999.JPG"]
    with pytest.raises(Phase1AnalysisPlanError, match="match analysis rows"):
        store.write(batch_id="batch-a", config_fingerprint="config-hash", **value)
