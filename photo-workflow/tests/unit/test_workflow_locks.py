# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_workflow_locks.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


import pytest

from app.workflow_locks import WorkflowLockError, WorkflowLockManager


def test_global_run_lock_blocks_a_second_productive_run(tmp_path) -> None:
    manager = WorkflowLockManager(tmp_path)
    first = manager.acquire_run_lock()

    with pytest.raises(WorkflowLockError, match="already held"):
        manager.acquire_run_lock()

    manager.release(first)
    second = manager.acquire_run_lock()
    manager.release(second)


def test_batch_lock_blocks_only_the_same_batch(tmp_path) -> None:
    manager = WorkflowLockManager(tmp_path)
    batch_a = manager.acquire_batch_lock("batch-a")

    with pytest.raises(WorkflowLockError):
        manager.acquire_batch_lock("batch-a")

    batch_b = manager.acquire_batch_lock("batch-b")
    manager.release(batch_b)
    manager.release(batch_a)


def test_non_owner_cannot_release_a_lock(tmp_path) -> None:
    manager = WorkflowLockManager(tmp_path)
    lock = manager.acquire_batch_lock("batch-a")
    forged = type(lock)(
        path=lock.path,
        scope=lock.scope,
        resource_id=lock.resource_id,
        owner_token="wrong-owner",
        acquired_at=lock.acquired_at,
    )

    with pytest.raises(WorkflowLockError, match="owner"):
        manager.release(forged)

    manager.release(lock)