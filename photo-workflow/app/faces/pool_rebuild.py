from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


class PoolRebuildError(ValueError):
    """Raised when a reference pool cannot be rebuilt safely."""


def _fingerprint(images: list[dict], model_fingerprint: str,
                preprocessing_fingerprint: str) -> str:
    payload = json.dumps({"images": images, "model": model_fingerprint,
                          "preprocessing": preprocessing_fingerprint},
                         ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def rebuild_pool(pool_root: str | Path, *, pool_type: str, slug: str | None,
                 images: list[dict], limits: dict, model_fingerprint: str,
                 preprocessing_fingerprint: str) -> dict:
    root = Path(pool_root)
    active = [dict(image) for image in images if image.get("status") == "active"]
    max_active = int(limits.get("max_active", len(active)))
    if len(active) > max_active:
        raise PoolRebuildError("max_active exceeded")
    for image in active:
        if any(key in image for key in ("embedding", "embeddings", "image_bytes")):
            raise PoolRebuildError("Embeddings or image bytes are forbidden")
        if not image.get("path"):
            raise PoolRebuildError("Active image path is required")
        image["pool_rank"] = 0
    active.sort(key=lambda item: (-float(item.get("pool_utility_score", 0.0)),
                                str(item["path"])))
    for rank, image in enumerate(active, 1):
        image["pool_rank"] = rank
        image["approved_at"] = image.get("approved_at") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    all_images = active + [dict(image) for image in images if image.get("status") == "new"]
    payload = {"schema_version": 1, "pool_type": pool_type,
               "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
               "selection_fingerprint": _fingerprint(all_images, model_fingerprint, preprocessing_fingerprint),
               "pool_build_id": hashlib.sha256(os.urandom(16)).hexdigest()[:16],
               "rank_digits": max(1, len(str(max(1, len(active))))),
               "limits": dict(limits), "images": all_images,
               "model_fingerprint": model_fingerprint,
               "preprocessing_fingerprint": preprocessing_fingerprint}
    if slug is not None:
        payload["slug"] = slug
    root.mkdir(parents=True, exist_ok=True)
    target = root / "selection.json"
    fd, temporary = tempfile.mkstemp(prefix=".selection.", dir=root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return payload


class RuntimeReferenceCache:
    def __init__(self):
        self.fingerprint: str | None = None
        self.values: dict = {}

    def get_or_rebuild(self, fingerprint: str, builder):
        if self.fingerprint != fingerprint:
            self.values = builder()
            self.fingerprint = fingerprint
        return self.values
