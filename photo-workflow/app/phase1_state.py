from __future__ import annotations

from typing import Any

from .state_store import StateStore


PHASE1_STATES = {"phase1_started", "phase1_moving", "phase1_completed"}
BLOCKING_STATES = {"quarantined", "review_state_invalid"}
_ALLOWED = {
    "phase1_started": {"phase1_moving", "quarantined", "review_state_invalid"},
    "phase1_moving": {"phase1_completed", "quarantined", "review_state_invalid"},
    "phase1_completed": set(),
    "quarantined": set(),
    "review_state_invalid": set(),
}


class Phase1TransitionError(ValueError):
    """Raised when a PHASE1 transition violates the state contract."""


def transition(store: StateStore, batch_id: str, target: str,
               *, producer_version: str, reason: str | None = None,
               **fields: Any) -> dict[str, Any]:
    current = store.read(batch_id)
    current_state = current.get("state") if current else None
    if target not in PHASE1_STATES | BLOCKING_STATES:
        raise Phase1TransitionError(f"Unknown PHASE1 state: {target}")
    if current_state is not None and target not in _ALLOWED.get(current_state, set()):
        raise Phase1TransitionError(f"Invalid PHASE1 transition: {current_state} -> {target}")
    return store.write(batch_id, target, producer_version=producer_version,
                       reason=reason, **fields)


def assert_phase1_completed(store: StateStore, batch_id: str) -> None:
    record = store.read(batch_id)
    if not record or record.get("state") != "phase1_completed":
        raise Phase1TransitionError(f"Batch is not phase1_completed: {batch_id}")
