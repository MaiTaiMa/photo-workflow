# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_runtime_control.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


import pytest

from app.runtime_control import RuntimeControl


def test_stop_prevents_a_new_expensive_step() -> None:
    control = RuntimeControl()

    assert control.before_expensive_step("before_scoring") is True
    control.request_stop()

    assert control.before_expensive_step("before_move") is False
    assert control.last_checkpoint == "before_move"


def test_pause_request_contains_reason_checkpoint_and_workunit() -> None:
    control = RuntimeControl()
    control.request_stop()

    request = control.pause_request("after_workunit", "batch-a:0002")

    assert request is not None
    assert request.reason == "stop_requested"
    assert request.checkpoint == "after_workunit"
    assert request.workunit_id == "batch-a:0002"
    assert control.paused is True


def test_pause_request_is_absent_without_stop_request() -> None:
    control = RuntimeControl()

    assert control.pause_request("before_move") is None

@pytest.mark.parametrize(
    "reason",
    (
        "max_runtime_seconds_per_run",
        "max_runtime_seconds_per_batch",
    ),
)
def test_budget_stop_creates_pause_request(reason: str) -> None:
    control = RuntimeControl()

    control.request_budget_stop(reason)
    request = control.pause_request("before_phase1_workunit", "wu-1")

    assert request is not None
    assert request.reason == reason
    assert request.checkpoint == "before_phase1_workunit"
    assert request.workunit_id == "wu-1"


def test_unknown_budget_stop_reason_is_rejected() -> None:
    control = RuntimeControl()

    with pytest.raises(ValueError, match="unsupported"):
        control.request_budget_stop("unknown_budget")