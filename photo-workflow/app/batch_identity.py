from __future__

import hashlib
from pathlib import Path


def _inventory(folder: Path) -> list[str]:
    rows = []
    for path in sorted(folder.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        stat = path.stat()
        rows.append(f"{path.relative_to(folder)}\0{stat.st_size}\0{stat.st_mtime_ns}")
    return rows


def batch_fingerprint(folder: str | Path) -> str:
    root = Path(folder)
    payload = "\n".join(_inventory(root)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:8]


def batch_id(folder: str | Path) -> str:
    root = Path(folder)
    return f"{root.name}+{batch_fingerprint(root)}"
