from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(batch_id: str, batch_root: str | Path, *, entries: list[dict],
                   csv_path: str | Path | None, config_fingerprint: str,
                   producer_version: str, counters: dict) -> dict:
    root = Path(batch_root)
    files = []
    for entry in entries:
        relative = Path(entry["relative_path"])
        source = root / relative
        if not source.is_file():
            raise ValueError(f"Manifest source is missing: {relative}")
        files.append({"relative_path": str(relative), "size": source.stat().st_size,
                      "hash": _sha256(source)})
    csv_hash = _sha256(Path(csv_path)) if csv_path else None
    return {
        "schema_version": 1,
        "batch_id": batch_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config_fingerprint": config_fingerprint,
        "producer_version": producer_version,
        "files": files,
        "culling_scores_hash": csv_hash,
        "counters": dict(counters),
        "phase1_status": "phase1_completed",
    }


def write_manifest(path: str | Path, manifest: dict) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return digest
