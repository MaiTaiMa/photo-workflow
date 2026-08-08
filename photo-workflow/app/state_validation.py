from __future__ import annotations

import hashlib
import json
from typing import Any

from .state_store import StateStore


class StateValidationError(ValueError):
    """Raised when a persisted state record is incomplete or tampered with."""


def validate_record(record: dict[str, Any]) -> None:
    required = {"batch_id", "state", "timestamp", "hash", "producer_version"}
    missing = required - record.keys()
    if missing:
        raise StateValidationError(f"Missing state fields: {sorted(missing)}")
    unsigned = dict(record)
    actual = unsigned.pop("hash")
    payload = json.dumps(unsigned, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"))
    expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    if actual != expected:
        raise StateValidationError("State hash mismatch")


def validate_current_state(store: StateStore, batch_id: str) -> dict[str, Any]:
    record = store.read(batch_id)
    if record is None:
        raise StateValidationError(f"State does not exist: {batch_id}")
    validate_record(record)
    return record
