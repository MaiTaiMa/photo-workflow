# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/faces/proposal_contract.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-09-03
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class FaceProposalError(ValueError):
    """Beschreibt einen ungültigen oder abgelehnten Face-Vorschlag."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_identifier(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FaceProposalError(f"{field} must be a non-empty string")
    if Path(value).name != value or value in {".", ".."}:
        raise FaceProposalError(f"{field} must not contain path separators")
    return value


def _load_selection(path: Path, *, pool_root: Path, slug: str, limits: dict[str, int]) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": 1,
            "pool_type": "face",
            "slug": slug,
            "updated_at": _now(),
            "selection_fingerprint": "",
            "pool_build_id": "proposal-init",
            "rank_digits": 1,
            "limits": dict(limits),
            "images": [],
        }

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FaceProposalError(f"cannot load selection.json: {exc}") from exc

    if payload.get("pool_type") != "face" or payload.get("slug") != slug:
        raise FaceProposalError("selection.json does not belong to this face pool")
    images = payload.get("images", [])
    if not isinstance(images, list):
        raise FaceProposalError("selection.json images must be a list")

    allowed_statuses = {"active", "new", "unknown"}
    forbidden_keys = {"embedding", "embeddings", "image_bytes"}
    for index, item in enumerate(images):
        if not isinstance(item, dict):
            raise FaceProposalError(f"selection.json images[{index}] must be an object")
        if forbidden_keys.intersection(item):
            raise FaceProposalError(f"selection.json images[{index}] contains forbidden data")
        if item.get("status") not in allowed_statuses:
            raise FaceProposalError(f"selection.json images[{index}] has invalid status")
        item_path = item.get("path") or item.get("rel_path")
        if not isinstance(item_path, str) or not item_path.strip():
            raise FaceProposalError(f"selection.json images[{index}] path is missing")
        normalized = Path(item_path)
        if normalized.is_absolute() or ".." in normalized.parts:
            raise FaceProposalError(f"selection.json images[{index}] path is unsafe")
        if item.get("status") == "new" and not item.get("batch_id"):
            raise FaceProposalError(f"selection.json images[{index}] batch_id is missing")

    payload["limits"] = dict(limits)
    return payload


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def add_face_proposal(
    pool_root: str | Path,
    *,
    slug: str,
    source_id: str,
    batch_id: str,
    crop_path: str | Path,
    original_path: str | Path,
    quality_score: float,
    candidate_utility_score: float,
    bounding_box: dict[str, int],
    face_confidence: float,
    limits: dict[str, int],
) -> dict[str, Any]:
    """Registriert einen neuen Face-Vorschlag ohne Bilddaten oder Embeddings."""
    _validate_identifier(slug, "slug")
    _validate_identifier(source_id, "source_id")
    _validate_identifier(batch_id, "batch_id")

    if not 0 <= float(quality_score) <= 1:
        raise FaceProposalError("quality_score must be between 0 and 1")
    if not 0 <= float(candidate_utility_score) <= 1:
        raise FaceProposalError("candidate_utility_score must be between 0 and 1")
    if not 0 <= float(face_confidence) <= 1:
        raise FaceProposalError("face_confidence must be between 0 and 1")

    required_box = {"left", "top", "right", "bottom"}
    if set(bounding_box) != required_box:
        raise FaceProposalError("bounding_box must contain exactly four coordinates")

    normalized_limits = {
        "max_new": int(limits["max_new"]),
        "max_new_per_batch": int(limits["max_new_per_batch"]),
    }
    if normalized_limits["max_new"] < 0:
        raise FaceProposalError("max_new must be non-negative")
    if normalized_limits["max_new_per_batch"] < 1:
        raise FaceProposalError("max_new_per_batch must be positive")
    if normalized_limits["max_new_per_batch"] > normalized_limits["max_new"]:
        raise FaceProposalError("max_new_per_batch must not exceed max_new")

    root = Path(pool_root)
    selection_path = root / "selection.json"
    payload = _load_selection(
        selection_path,
        pool_root=root,
        slug=slug,
        limits=normalized_limits,
    )
    images = payload["images"]
    new_images = [item for item in images if item.get("status") == "new"]
    batch_images = [item for item in new_images if item.get("batch_id") == batch_id]

    if len(new_images) >= normalized_limits["max_new"]:
        raise FaceProposalError("max_new reached")
    if len(batch_images) >= normalized_limits["max_new_per_batch"]:
        raise FaceProposalError("max_new_per_batch reached")

    crop = Path(crop_path)
    try:
        relative_crop = crop.relative_to(root)
    except ValueError as exc:
        raise FaceProposalError("crop_path must be inside the face pool") from exc
    if relative_crop.parts[:1] != ("new_faces",):
        raise FaceProposalError("crop_path must be inside new_faces")

    original = Path(original_path)
    entry = {
        "source_id": source_id,
        "batch_id": batch_id,
        "path": relative_crop.as_posix(),
        "status": "new",
        "quality_score": float(quality_score),
        "candidate_utility_score": float(candidate_utility_score),
        "bounding_box": dict(bounding_box),
        "face_confidence": float(face_confidence),
        "original_path": str(original),
        "added_at": _now(),
    }
    images.append(entry)
    payload["images"] = images
    payload["updated_at"] = _now()
    payload["limits"] = normalized_limits
    _atomic_write(selection_path, payload)
    return entry
