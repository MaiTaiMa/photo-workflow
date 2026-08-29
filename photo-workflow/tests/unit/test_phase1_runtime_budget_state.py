# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_phase1_runtime_budget_state.py
# PURPOSE:     Prüft atomare und hashvalidierte aktive Phase-1-Batch-Laufzeiten.
# AUTHOR:      Matzethias
# DATE:        2026-08-20
# VERSION:     1.0.0
# REQUIRES:    Python 3.11, pytest
# CHANGES:
#   2026-08-20 | 1.0.0 | B2.1: Tests für persistierte aktive Batch-Zeit ergänzt.
# =============================================================================


import json

import pytest

from app.phase1_runtime_budget_state import (
    Phase1RuntimeBudgetStateError,
    Phase1RuntimeBudgetStateStore,
)


def test_add_active_seconds_creates_hash_valid_state(tmp_path) -> None:
    store = Phase1RuntimeBudgetStateStore(tmp_path, "test-v1")

    record = store.add_active_seconds(batch_id="batch-a", seconds=1.25)

    assert record["active_seconds"] == 1.25
    assert record["previous_hash"] == ""
    assert store.load("batch-a") == record


def test_add_active_seconds_accumulates_and_hash_chains(tmp_path) -> None:
    store = Phase1RuntimeBudgetStateStore(tmp_path, "test-v1")

    first = store.add_active_seconds(batch_id="batch-a", seconds=1.25)
    second = store.add_active_seconds(batch_id="batch-a", seconds=2.75)

    assert second["active_seconds"] == 4.0
    assert second["previous_hash"] == first["hash"]
    assert store.load("batch-a") == second


@pytest.mark.parametrize(
    "seconds",
    (-1.0, True, "1.0", float("nan"), float("inf"), float("-inf")),
)
def test_invalid_active_seconds_are_rejected(tmp_path, seconds) -> None:
    store = Phase1RuntimeBudgetStateStore(tmp_path, "test-v1")

    with pytest.raises(Phase1RuntimeBudgetStateError, match="active_seconds"):
        store.add_active_seconds(batch_id="batch-a", seconds=seconds)


def test_hash_tampering_is_rejected(tmp_path) -> None:
    store = Phase1RuntimeBudgetStateStore(tmp_path, "test-v1")
    record = store.add_active_seconds(batch_id="batch-a", seconds=1.0)
    record["active_seconds"] = 999.0
    store.path_for("batch-a").write_text(
        json.dumps(record),
        encoding="utf-8",
    )

    with pytest.raises(Phase1RuntimeBudgetStateError, match="hash"):
        store.load("batch-a")


def test_unsafe_batch_id_is_rejected(tmp_path) -> None:
    store = Phase1RuntimeBudgetStateStore(tmp_path, "test-v1")

    with pytest.raises(Phase1RuntimeBudgetStateError, match="unsafe"):
        store.add_active_seconds(batch_id="../batch-a", seconds=1.0)