"""
Skript: app/runtime_budget.py
Zweck: Verwaltet zustandsfreie lokale Laufzeitbudgets ohne Workflow-Mutationen.
Autor: MaiTaiMa
Erstellt: 2026-08-20
Version: 1.0.0
Requires: Python 3.11

Änderungsprotokoll:
  2026-08-20 | 1.0.0 | B1: Monotones Zeitbudget für Run- und Batch-Grenzen ergänzt.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable


Clock = Callable[[], float]


@dataclass
class RuntimeBudget:
    """Misst ein optionales Zeitbudget ohne Dateien, States oder Stop-Anforderungen."""

    limit_seconds: int | None
    clock: Clock = time.monotonic
    started_at: float = field(init=False)

    def __post_init__(self) -> None:
        """Validiert das Budget und speichert den monotonic Startzeitpunkt."""
        if self.limit_seconds is not None:
            if (
                isinstance(self.limit_seconds, bool)
                or not isinstance(self.limit_seconds, int)
                or self.limit_seconds <= 0
            ):
                raise ValueError(
                    "limit_seconds must be null or a positive integer"
                )
        self.started_at = self.clock()

    @property
    def elapsed_seconds(self) -> float:
        """Liefert die seit Start vergangene, niemals negative Laufzeit."""
        return max(0.0, self.clock() - self.started_at)

    @property
    def remaining_seconds(self) -> float | None:
        """Liefert das Restbudget oder null für eine unbegrenzte Laufzeit."""
        if self.limit_seconds is None:
            return None
        return max(0.0, float(self.limit_seconds) - self.elapsed_seconds)

    @property
    def expired(self) -> bool:
        """Meldet ausschließlich die Budgetüberschreitung ohne Nebenwirkung."""
        return (
            self.limit_seconds is not None
            and self.elapsed_seconds >= float(self.limit_seconds)
        )
