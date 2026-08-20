"""
Skript: tests/unit/test_runtime_budget.py
Zweck: Prüft deterministisch das zustandsfreie Runtime-Budget.
Autor: MaiTaiMa
Erstellt: 2026-08-20
Version: 1.0.0
Requires: Python 3.11, pytest

Änderungsprotokoll:
  2026-08-20 | 1.0.0 | B1: Tests für Zeitbudget, Restzeit und Ablauf ergänzt.
"""

import pytest

from app.runtime_budget import RuntimeBudget


class ManualClock:
    """Liefert in Tests kontrollierbare monotone Zeitwerte."""

    def __init__(self, value: float = 0.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def test_unlimited_budget_never_expires() -> None:
    clock = ManualClock(10.0)
    budget = RuntimeBudget(limit_seconds=None, clock=clock)

    clock.value = 10_000.0

    assert budget.remaining_seconds is None
    assert budget.expired is False


def test_budget_tracks_elapsed_remaining_and_expiry() -> None:
    clock = ManualClock(100.0)
    budget = RuntimeBudget(limit_seconds=10, clock=clock)

    clock.value = 106.5

    assert budget.elapsed_seconds == 6.5
    assert budget.remaining_seconds == 3.5
    assert budget.expired is False

    clock.value = 110.0

    assert budget.remaining_seconds == 0.0
    assert budget.expired is True


def test_budget_never_reports_negative_elapsed_time() -> None:
    clock = ManualClock(100.0)
    budget = RuntimeBudget(limit_seconds=10, clock=clock)

    clock.value = 99.0

    assert budget.elapsed_seconds == 0.0
    assert budget.remaining_seconds == 10.0


@pytest.mark.parametrize("limit_seconds", (0, -1, True, 1.5, "60"))
def test_invalid_budget_values_are_rejected(limit_seconds: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        RuntimeBudget(limit_seconds=limit_seconds)  # type: ignore[arg-type]


def test_budget_includes_persisted_active_seconds() -> None:
    clock = ManualClock(100.0)
    budget = RuntimeBudget(
        limit_seconds=10,
        clock=clock,
        consumed_seconds=8.0,
    )

    assert budget.elapsed_seconds == 8.0
    assert budget.remaining_seconds == 2.0
    assert budget.expired is False

    clock.value = 102.0

    assert budget.elapsed_seconds == 10.0
    assert budget.remaining_seconds == 0.0
    assert budget.expired is True


@pytest.mark.parametrize(
    "consumed_seconds",
    (-1.0, True, "1.0", float("nan"), float("inf"), float("-inf")),
)
def test_invalid_persisted_active_seconds_are_rejected(
    consumed_seconds: object,
) -> None:
    with pytest.raises(ValueError, match="consumed_seconds"):
        RuntimeBudget(
            limit_seconds=10,
            consumed_seconds=consumed_seconds,  # type: ignore[arg-type]
        )
