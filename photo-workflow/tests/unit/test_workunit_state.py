from __future__ import annotations

import json

import pytest

from app.workunit_state import WorkUnitStateError, WorkUnitStateStore


def create_store(tmp_path):
    return WorkUnitStateStore(tmp_path, "test-v1")


def initialize(store):
    return store.initialize(
        batch_id="2026-08-17_Test",
        workunit_id="2026-08-17_Test:wu-0001",
        image_names=("IMG_0001.JPG", "IMG_0002.JPG"),
        config_fingerprint="config-hash",
    )


def test_initialize_creates_hash_valid_pending_state(tmp_path) -> None:
    store = create_store(tmp_path)

    record = initialize(store)

    assert record["state"] == "pending"
    assert record["next_image_index"] == 0
    assert store.load(record["batch_id"], record["workunit_id"]) == record


def test_transition_tracks_progress_and_completion(tmp_path) -> None:
    store = create_store(tmp_path)
    initial = initialize(store)

    in_progress = store.transition(
        batch_id=initial["batch_id"],
        workunit_id=initial["workunit_id"],
        new_state="in_progress",
        next_image_index=1,
    )
    completed = store.transition(
        batch_id=initial["batch_id"],
        workunit_id=initial["workunit_id"],
        new_state="completed",
        next_image_index=2,
    )

    assert in_progress["previous_state_hash"] == initial["hash"]
    assert completed["previous_state_hash"] == in_progress["hash"]
    assert completed["state"] == "completed"


def test_backward_transition_is_rejected(tmp_path) -> None:
    store = create_store(tmp_path)
    initial = initialize(store)
    store.transition(
        batch_id=initial["batch_id"],
        workunit_id=initial["workunit_id"],
        new_state="in_progress",
    )

    with pytest.raises(WorkUnitStateError, match="invalid transition"):
        store.transition(
            batch_id=initial["batch_id"],
            workunit_id=initial["workunit_id"],
            new_state="pending",
        )


def test_hash_tampering_is_rejected(tmp_path) -> None:
    store = create_store(tmp_path)
    record = initialize(store)
    path = store.path_for(record["batch_id"], record["workunit_id"])
    tampered = dict(record)
    tampered["next_image_index"] = 1
    path.write_text(json.dumps(tampered), encoding="utf-8")

    with pytest.raises(WorkUnitStateError, match="hash"):
        store.load(record["batch_id"], record["workunit_id"])


def test_next_pending_is_deterministic_and_skips_completed(tmp_path) -> None:
    store = create_store(tmp_path)
    first = initialize(store)
    second = store.initialize(
        batch_id=first["batch_id"],
        workunit_id="2026-08-17_Test:wu-0002",
        image_names=("IMG_0003.JPG",),
        config_fingerprint="config-hash",
    )
    store.transition(
        batch_id=first["batch_id"],
        workunit_id=first["workunit_id"],
        new_state="in_progress",
        next_image_index=2,
    )
    store.transition(
        batch_id=first["batch_id"],
        workunit_id=first["workunit_id"],
        new_state="completed",
        next_image_index=2,
    )

    assert store.next_pending(first["batch_id"])["workunit_id"] == second["workunit_id"]
