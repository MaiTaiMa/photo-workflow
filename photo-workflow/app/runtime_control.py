from __future__ import annotations

import signal
from dataclasses import dataclass


@dataclass
class RuntimeControl:
    paused: bool = False
    stop_requested: bool = False
    current_workunit: str | None = None

    def request_stop(self, *_args) -> None:
        self.stop_requested = True

    def before_expensive_step(self) -> bool:
        return not self.stop_requested

    def mark_paused(self, workunit_id: str | None = None) -> None:
        self.paused = True
        self.current_workunit = workunit_id


def install_signal_handlers(control: RuntimeControl) -> None:
    signal.signal(signal.SIGTERM, control.request_stop)
    signal.signal(signal.SIGINT, control.request_stop)
