"""
Skript: app/runtime_control.py
Zweck: Hält Stop-Anforderungen und sichere Pause-Checkpoints im Arbeitsspeicher.
Autor: MaiTaiMa
Erstellt: 2026-08-08
Version: 1.2.0
Requires: Python 3.11

Änderungsprotokoll:
  2026-08-08 | 1.0.0 | Initiale Runtime-Control ergänzt.
  2026-08-20 | 1.2.0 | B2.1: Explizite Budget-Stop-Gründe ergänzt.
  2026-08-14 | 1.1.0 | V12-02: Strukturierte Stop- und Checkpoint-Daten ergänzt.
"""

from __future__ import annotations

import signal
from dataclasses import dataclass


@dataclass(frozen=True)
class PauseRequest:
    """Beschreibt einen sicheren, später persistent zu speichernden Pause-Checkpoint."""

    reason: str
    checkpoint: str
    workunit_id: str | None = None


@dataclass
class RuntimeControl:
    """Empfängt Signale und erlaubt Stop-Prüfungen nur an sicheren Grenzen."""

    stop_requested: bool = False
    stop_reason: str | None = None
    paused: bool = False
    current_workunit: str | None = None
    last_checkpoint: str | None = None

    def request_stop(self, signal_number: int | None = None, *_args: object) -> None:
        """Registriert eine Stop-Anforderung ohne Dateien oder States zu verändern."""
        self.stop_requested = True
        if self.stop_reason is None:
            self.stop_reason = (
                f"signal_{signal_number}" if signal_number is not None else "stop_requested"
            )

    def request_budget_stop(self, reason: str) -> None:
        """Registriert einen validierten Budget-Stop ohne State-Mutation."""
        if reason not in {
            "max_runtime_seconds_per_run",
            "max_runtime_seconds_per_batch",
        }:
            raise ValueError("unsupported runtime budget stop reason")
        self.stop_requested = True
        self.stop_reason = reason

    def before_expensive_step(
        self,
        checkpoint: str = "unspecified",
    ) -> bool:
        """
        Prüft vor einem neuen teuren Schritt, ob ein sicherer Stop erforderlich ist.

        Der optionale Default erhält die Kompatibilität mit bestehenden Aufrufern.
        Neue Workflow-Aufrufe müssen einen konkreten sicheren Checkpoint übergeben.
        """
        self.last_checkpoint = checkpoint
        return not self.stop_requested

    def mark_paused(
        self,
        workunit_id: str | None = None,
    ) -> None:
        """
        Markiert den Runtime-Control-Zustand als pausiert.

        Diese Kompatibilitätsmethode schreibt keine Dateien. Die dauerhafte,
        atomare Persistenz erfolgt ausschließlich über PauseCheckpointStore
        und persist_pause_if_requested() an einem sicheren Checkpoint.
        """
        self.paused = True
        self.current_workunit = workunit_id

    def pause_request(
        self,
        checkpoint: str,
        workunit_id: str | None = None,
    ) -> PauseRequest | None:
        """Erzeugt nur nach einer Stop-Anforderung einen kontrollierten Pauseauftrag."""
        if not self.stop_requested:
            return None
        self.paused = True
        self.last_checkpoint = checkpoint
        self.current_workunit = workunit_id
        return PauseRequest(
            reason=self.stop_reason or "stop_requested",
            checkpoint=checkpoint,
            workunit_id=workunit_id,
        )


def install_signal_handlers(control: RuntimeControl) -> None:
    """Registriert SIGTERM und SIGINT; Handler setzen ausschließlich den Stop-Status."""
    signal.signal(signal.SIGTERM, control.request_stop)
    signal.signal(signal.SIGINT, control.request_stop)