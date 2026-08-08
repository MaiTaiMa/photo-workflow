from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class InventoryEntry:
    relative_path: str
    size: int
    mtime_ns: int
    sha256: str


def _sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def collect_inventory(root: str | Path) -> list[InventoryEntry]:
    base = Path(root)
    entries = []
    for path in sorted(base.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        stat = path.stat()
        entries.append(InventoryEntry(str(path.relative_to(base)), stat.st_size,
                                      stat.st_mtime_ns, _sha256(path)))
    return entries


def inventory_fingerprint(entries: list[InventoryEntry]) -> str:
    payload = "\n".join(
        f"{entry.relative_path}\0{entry.size}\0{entry.mtime_ns}\0{entry.sha256}"
        for entry in entries
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def stable_inventory(root: str | Path, wait_seconds: float = 1.0) -> tuple[list[InventoryEntry], str]:
    first = collect_inventory(root)
    if wait_seconds > 0:
        time.sleep(wait_seconds)
    second = collect_inventory(root)
    if first != second:
        raise RuntimeError("Batch is not stable: inventory changed during observation")
    return second, inventory_fingerprint(second)


def write_inventory(path: str | Path, entries: list[InventoryEntry], fingerprint: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    value = {
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "entry_count": len(entries),
        "inventory_hash": fingerprint,
        "entries": [asdict(entry) for entry in entries],
    }
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
