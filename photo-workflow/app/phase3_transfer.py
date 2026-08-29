# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/phase3_transfer.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path

from .path_security import ensure_within, validate_publish_target


class TransferError(ValueError):
    """Raised when PHASE3 transfer verification fails."""


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _files(root: Path) -> list[dict]:
    result = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            result.append({"relative_path": str(path.relative_to(root)),
                           "size": path.stat().st_size, "hash": _hash(path)})
    return result


def transfer_batch(source: str | Path, target: str | Path, config: dict, *,
                   batch_id: str, mode: str = "copy", dry_run: bool = False) -> dict:
    source_path = ensure_within(config["paths"].get("basedir", config["paths"].get("base_dir")),
                                source, allow_missing=False)
    target_path = validate_publish_target(config, target)
    if mode not in {"copy", "move"}:
        raise TransferError(f"Unsupported transfer mode: {mode}")
    manifest = {"batch_id": batch_id, "source_batch_path": str(source_path),
                "target_batch_path": str(target_path), "transfer_mode": mode,
                "files": _files(source_path)}
    if dry_run:
        manifest["status"] = "planned"
        return manifest
    target_path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target_path.name}.", dir=target_path.parent))
    try:
        shutil.copytree(source_path, staging / source_path.name)
        staged = staging / source_path.name
        if _files(source_path) != _files(staged):
            raise TransferError("Target verification failed")
        if target_path.exists():
            raise TransferError(f"Target already exists: {target_path}")
        os.replace(staged, target_path)
        if mode == "move":
            shutil.rmtree(source_path)
        manifest["status"] = "transferred"
        manifest["target_files"] = _files(target_path)
        return manifest
    finally:
        shutil.rmtree(staging, ignore_errors=True)
