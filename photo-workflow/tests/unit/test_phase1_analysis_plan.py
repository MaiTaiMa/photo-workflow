# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_phase1_analysis_plan.py
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

def test_analysis_plan_accepts_safe_execution_fields(tmp_path) -> None:
    store = Phase1AnalysisPlanStore(tmp_path, "test-v1")
    value = payload()

    value["rows"][0]["family_tags"] = [
        "family:match:true",
        "person:kind1",
    ]
    value["rows"][0]["family_regions"] = [
        {
            "name": "kind1",
            "left": 10,
            "top": 20,
            "right": 120,
            "bottom": 180,
            "distance": 0.21,
        }
    ]
    value["rows"][0]["execution"] = {
        "target_relative_path": "IMG_0001.JPG",
        "moved": False,
        "family_metadata_written": False,
        "culling_metadata_written": False,
    }

    record = store.write(
        batch_id="batch-a",
        config_fingerprint="config-hash",
        **value,
    )

    assert record["rows"][0]["execution"]["moved"] is False
    assert record["rows"][0]["family_tags"] == [
        "family:match:true",
        "person:kind1",
    ]

def test_analysis_plan_rejects_unsafe_execution_target(tmp_path) -> None:
    store = Phase1AnalysisPlanStore(tmp_path, "test-v1")
    value = payload()

    value["rows"][0]["execution"] = {
        "target_relative_path": "../outside.JPG",
        "moved": False,
        "family_metadata_written": False,
        "culling_metadata_written": False,
    }

    with pytest.raises(
        Phase1AnalysisPlanError,
        match="unsafe",
    ):
        store.write(
            batch_id="batch-a",
            config_fingerprint="config-hash",
            **value,
        )

def test_analysis_plan_rejects_unsupported_region_payload(tmp_path) -> None:
    store = Phase1AnalysisPlanStore(tmp_path, "test-v1")
    value = payload()

    value["rows"][0]["family_regions"] = [
        {
            "name": "kind1",
            "left": 10,
            "top": 20,
            "right": 120,
            "bottom": 180,
            "embedding": [0.1, 0.2],
        }
    ]

    with pytest.raises(
        Phase1AnalysisPlanError,
        match="unsupported fields",
    ):
        store.write(
            batch_id="batch-a",
            config_fingerprint="config-hash",
            **value,
        )

    def test_analysis_plan_updates_execution_atomically(tmp_path) -> None:
        store = Phase1AnalysisPlanStore(tmp_path, "test-v1")
        value = payload()

        value["rows"][0]["execution"] = {
            "target_relative_path": "IMG_0001.JPG",
            "moved": False,
            "family_metadata_written": False,
            "culling_metadata_written": False,
        }

        initial = store.write(
            batch_id="batch-a",
            config_fingerprint="config-hash",
            **value,
        )

        updated = store.update_execution(
            batch_id="batch-a",
            file_name="IMG_0001.JPG",
            moved=True,
            family_metadata_written=True,
        )

        execution = updated["rows"][0]["execution"]

        assert execution["moved"] is True
        assert execution["family_metadata_written"] is True
        assert execution["culling_metadata_written"] is False

        assert updated["previous_hash"] == initial["hash"]
        assert updated["hash"] != initial["hash"]
        assert updated["updated_at"] >= initial["created_at"]

        assert store.load("batch-a") == updated

    def test_analysis_plan_rejects_execution_update_for_unknown_file(
        tmp_path,
    ) -> None:
        store, _ = write_plan(tmp_path)

        with pytest.raises(
            Phase1AnalysisPlanError,
            match="not part of analysis plan",
        ):
            store.update_execution(
                batch_id="batch-a",
                file_name="IMG_9999.JPG",
                moved=True,
            )