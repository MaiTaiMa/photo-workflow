from __future__ import annotations

import hashlib
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


class ArchiveError(ValueError):
    """Raised when an archive is incomplete, unsafe or collides."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def archive_entries(root: str | Path, paths: list[str | Path]) -> list[dict]:
    base = Path(root).resolve()
    entries = []
    for value in paths:
        source = (base / value).resolve()
        try:
            relative = source.relative_to(base)
        except ValueError as exc:
            raise ArchiveError(f"Archive path escapes batch: {value}") from exc
        if not source.is_file() or source.is_symlink():
            raise ArchiveError(f"Archive source is missing or unsafe: {value}")
        entries.append({"relative_path": str(relative), "size": source.stat().st_size,
                        "hash": _sha256(source),
                        "archived_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")})
    return entries


def _safe_target(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    index = 2
    while True:
        candidate = path.with_name(f"{stem}_EXTRA{index}{suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def create_verified_zip(root: str | Path, target: str | Path,
                        paths: list[str | Path], *, batch_id: str,
                        config_fingerprint: str, producer_version: str) -> dict:
    base = Path(root).resolve()
    requested = Path(target)
    destination = _safe_target(requested)
    entries = archive_entries(base, paths)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.",
                                     suffix=".zip", dir=destination.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for entry in entries:
                archive.write(base / entry["relative_path"], entry["relative_path"])
        with zipfile.ZipFile(temporary) as archive:
            names = archive.namelist()
            if set(names) != {entry["relative_path"] for entry in entries}:
                raise ArchiveError("Archive file list verification failed")
            for name in names:
                if Path(name).is_absolute() or ".." in Path(name).parts:
                    raise ArchiveError("Archive traversal entry detected")
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"batch_id": batch_id, "archive_path": str(destination),
            "entry_count": len(entries), "total_size": sum(e["size"] for e in entries),
            "entries": entries, "archive_hash": _sha256(destination),
            "config_fingerprint": config_fingerprint,
            "producer_version": producer_version}
