"""
Skript: app/personal_score_cache.py
Zweck: Versionierter Cache für CLIP-Referenz-Embeddings mit sicherer Invalidierung.
Version: 1.0.0
"""

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable


CACHE_SCHEMA_VERSION = "1.0"
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_reference_images(reference_dir: str | Path) -> list[Path]:
    """Return deterministic, regular image files below one reference directory."""
    root = Path(reference_dir)
    if not root.exists():
        return []
    if not root.is_dir():
        raise ValueError("reference path must be a directory")
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink() and path.suffix.lower() in _IMAGE_SUFFIXES
    )


def reference_fingerprint(reference_dir: str | Path) -> tuple[str, list[Path]]:
    """Hash relative paths and content of every active personal-score reference image."""
    root = Path(reference_dir)
    paths = iter_reference_images(root)
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(_sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest(), paths


def _is_embedding(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(component, (int, float)) and not isinstance(component, bool) for component in value)
    )


def _load_cache(cache_path: Path, *, model_id: str, fingerprint: str) -> dict[str, list[float]] | None:
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != CACHE_SCHEMA_VERSION:
        return None
    if payload.get("model_id") != model_id or payload.get("reference_fingerprint") != fingerprint:
        return None
    embeddings = payload.get("embeddings")
    if not isinstance(embeddings, dict) or not all(
        isinstance(path, str) and _is_embedding(vector) for path, vector in embeddings.items()
    ):
        return None
    return {path: [float(component) for component in vector] for path, vector in embeddings.items()}


def _write_cache(
    cache_path: Path,
    *,
    model_id: str,
    fingerprint: str,
    embeddings: dict[str, list[float]],
) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "model_id": model_id,
        "reference_fingerprint": fingerprint,
        "reference_count": len(embeddings),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "embeddings": embeddings,
    }
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=cache_path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        temporary_path = Path(handle.name)
    os.replace(temporary_path, cache_path)


def load_or_build_reference_cache(
    *,
    reference_dir: str | Path,
    cache_path: str | Path,
    model_id: str,
    embed: Callable[[Path], Iterable[float]],
) -> tuple[dict[str, list[float]], bool]:
    """Load matching embeddings or rebuild when references, model, or cache are invalid."""
    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError("model_id is required")
    root = Path(reference_dir)
    fingerprint, paths = reference_fingerprint(root)
    target = Path(cache_path)
    cached = _load_cache(target, model_id=model_id, fingerprint=fingerprint)
    expected_paths = {path.relative_to(root).as_posix() for path in paths}
    if cached is not None and set(cached) == expected_paths:
        return cached, True

    embeddings: dict[str, list[float]] = {}
    for path in paths:
        vector = list(embed(path))
        if not _is_embedding(vector) or not vector:
            raise ValueError(f"embedder returned no numeric embedding for {path}")
        embeddings[path.relative_to(root).as_posix()] = [float(component) for component in vector]
    _write_cache(target, model_id=model_id, fingerprint=fingerprint, embeddings=embeddings)
    return embeddings, False
