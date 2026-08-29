# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/recovery.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path


def quarantine_batch(source: str | Path, quarantine_root: str | Path, *, reason: str,
                     batch_id: str) -> Path:
    source_path = Path(source)
    root = Path(quarantine_root)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = root / f"{batch_id}_{timestamp}"
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_path, destination, symlinks=False)
    (destination / "QUARANTINE_REASON.txt").write_text(
        f"batch_id={batch_id}\nreason={reason}\n", encoding="utf-8")
    return destination