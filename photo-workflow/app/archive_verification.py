from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

from .archive_contract import ArchiveError


def _hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def verify_zip_against_source(zip_path: str | Path, source_root: str | Path,
                              entries: list[dict]) -> None:
    archive = Path(zip_path)
    root = Path(source_root).resolve()
    expected = {entry["relative_path"]: entry for entry in entries}
    with zipfile.ZipFile(archive) as handle:
        if set(handle.namelist()) != set(expected):
            raise ArchiveError("Archive entries differ from manifest")
        for name, entry in expected.items():
            data = handle.read(name)
            source = root / name
            if not source.is_file() or source.is_symlink():
                raise ArchiveError(f"Source missing during archive verification: {name}")
            if len(data) != int(entry["size"]):
                raise ArchiveError(f"Archive size mismatch: {name}")
            if _hash_bytes(data) != entry["hash"]:
                raise ArchiveError(f"Archive hash mismatch: {name}")
            if source.stat().st_size != int(entry["size"]):
                raise ArchiveError(f"Source size changed: {name}")
