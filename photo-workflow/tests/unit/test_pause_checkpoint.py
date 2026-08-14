import pytest

from app.pause_checkpoint import PauseCheckpointError, PauseCheckpointStore


def test_pause_checkpoint_round_trip_is_hash_valid(tmp_path) -> None:
    store = PauseCheckpointStore(tmp_path, "test-v1")

    written = store.write(
        batch_id="batch-a",
        pause_reason="signal_15",
        checkpoint="after_workunit",
        workunit_id="batch-a:0002",
        config_fingerprint="config-hash",
        previous_state_hash="previous-hash",
    )

    loaded = store.load("batch-a")

    assert loaded == written
    assert loaded["state"] == "paused"
    assert loaded["workunit_id"] == "batch-a:0002"


def test_pause_checkpoint_rejects_hash_tampering(tmp_path) -> None:
    store = PauseCheckpointStore(tmp_path, "test-v1")
    record = store.write(
        batch_id="batch-a",
        pause_reason="signal_15",
        checkpoint="before_move",
        config_fingerprint="config-hash",
        previous_state_hash="previous-hash",
    )
    record["pause_reason"] = "forged"
    store.path_for("batch-a").write_text(__import__("json").dumps(record), encoding="utf-8")

    with pytest.raises(PauseCheckpointError, match="hash"):
        store.load("batch-a")


def test_pause_checkpoint_does_not_exist_until_written(tmp_path) -> None:
    store = PauseCheckpointStore(tmp_path, "test-v1")

    assert store.load("batch-a") is None