from __future__

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _digest(payload: dict[str, Any]) -> str:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class StateStore:
    """Stores one atomically replaced, hash-chained state record per batch."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def path_for(self, batch_id: str) -> Path:
        safe = batch_id.replace("/", "_").replace("\\", "_")
        return self.root / f"{safe}.json"

    def read(self, batch_id: str) -> dict[str, Any] | None:
        path = self.path_for(batch_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write(self, batch_id: str, state: str, *, producer_version: str,
              reason: str | None = None, **fields: Any) -> dict[str, Any]:
        previous = self.read(batch_id)
        record: dict[str, Any] = {
            "batch_id": batch_id,
            "state": state,
            "timestamp": _now(),
            "hash": "",
            "previous_state_hash": previous.get("hash") if previous else None,
            "producer_version": producer_version,
        }
        if reason is not None:
            record["reason"] = reason
        record.update(fields)
        unsigned = dict(record)
        unsigned["hash"] = ""
        record["hash"] = _digest(unsigned)
        self._atomic_write(self.path_for(batch_id), record)
        return record

    @staticmethod
    def _atomic_write(path: Path, value: dict[str, Any]) -> None:
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
