from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


class ReviewRecordError(ValueError):
    """Raised when a review record is missing or would be overwritten."""


def _digest(value: dict) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_review_record(path: str | Path, *, batch_id: str,
                        human_decision: str, predicted_decision: str,
                        config_fingerprint: str, producer_version: str,
                        image_count: int) -> str:
    target = Path(path)
    if target.exists():
        raise ReviewRecordError(f"Review record already exists: {target}")
    record = {"schema_version": 1, "batch_id": batch_id,
              "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
              "human_decision": human_decision,
              "predicted_decision": predicted_decision,
              "agreement": human_decision == predicted_decision,
              "config_fingerprint": config_fingerprint,
              "producer_version": producer_version,
              "image_count": image_count}
    record["record_hash"] = _digest(record)
    _atomic_write(target, record)
    return record["record_hash"]


def write_calibration_index(path: str | Path, *, batch_id: str,
                            review_record_hash: str, metrics: dict) -> None:
    target = Path(path)
    if target.exists():
        raise ReviewRecordError(f"Calibration index already exists: {target}")
    _atomic_write(target, {"schema_version": 1, "batch_id": batch_id,
                           "review_record_hash": review_record_hash,
                           "metrics": dict(metrics)})


def _atomic_write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
