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