from __future__ import annotations

import hashlib
import json
from pathlib import Path


class ReferencePoolError(ValueError):
    """Raised when a reference pool violates its selection contract."""


def _fingerprint(images: list[dict]) -> str:
    payload = json.dumps(images, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_active_references(pool_root: str | Path, *, pool_type: str,
                           slug: str | None = None) -> tuple[dict, list[Path]]:
    root = Path(pool_root)
    selection_path = root / "selection.json"
    if not selection_path.exists():
        raise ReferencePoolError(f"Missing selection.json: {root}")
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    required = {"schema_version", "pool_type", "updated_at",
                "selection_fingerprint", "pool_build_id", "rank_digits",
                "limits", "images"}
    missing = required - selection.keys()
    if missing:
        raise ReferencePoolError(f"Missing selection fields: {sorted(missing)}")
    if selection["pool_type"] != pool_type:
        raise ReferencePoolError("Reference pool type mismatch")
    if pool_type == "face" and selection.get("slug") != slug:
        raise ReferencePoolError("Face pool slug mismatch")
    if any(key in entry for key in ("embedding", "embeddings", "image_bytes")
           for entry in selection["images"]):
        raise ReferencePoolError("Binary data or embeddings in selection.json")
    active = []
    for entry in selection["images"]:
        if entry.get("status") != "active":
            continue
        path = root / "reference" / Path(entry["path"]).name
        if not path.exists() or path.is_symlink():
            raise ReferencePoolError(f"Active reference missing or unsafe: {path}")
        active.append(path)
    if selection["selection_fingerprint"] != _fingerprint(selection["images"]):
        raise ReferencePoolError("selection_fingerprint mismatch")
    return selection, active
