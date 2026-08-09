"""
Skript: app/faces/pool_rebuild.py
Zweck: Baut Referenzpool-Auswahlen atomar ohne Embedding-Persistenz neu auf.
Autor: MaiTaiMa
Erstellt: 2026-08-08
Version: 1.2
Requires: Python 3.11

Änderungsprotokoll:
  2026-08-08 | 1.2 | AP22 Pool-Rebuild nach 98AP formatiert
"""

from __future__ import annotations

# === Standardbibliothek ===
# Zweck: Erzeugt Fingerprints, JSON-Auswahlen und atomare Pool-Artefakte.
# Eingabe: Bildauswahl, Limits sowie Modell- und Preprocessing-Fingerprint.
# Ausgabe: Atomar aktivierte selection.json ohne Embeddings oder Bildbytes.
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


class PoolRebuildError(ValueError):
    """Beschreibt einen Fehler beim sicheren Neuaufbau eines Referenzpools."""


def _now() -> str:
    """Gibt einen UTC-Zeitstempel im kanonischen ISO-8601-Format zurück."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _fingerprint(
    images: list[dict],
    model_fingerprint: str,
    preprocessing_fingerprint: str,
) -> str:
    """Berechnet den kanonischen Fingerprint von Auswahl und Verarbeitung."""
    payload = json.dumps(
        {
            "images": images,
            "model": model_fingerprint,
            "preprocessing": preprocessing_fingerprint,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def rebuild_pool(
    pool_root: str | Path,
    *,
    pool_type: str,
    slug: str | None,
    images: list[dict],
    limits: dict,
    model_fingerprint: str,
    preprocessing_fingerprint: str,
) -> dict:
    """
    Erstellt eine begrenzte Referenzauswahl und aktiviert sie atomar.

    Embeddings und Bildbytes werden vollständig aus dem JSON-Artefakt entfernt.
    """
    root = Path(pool_root)
    active = [
        dict(image)
        for image in images
        if image.get("status") == "active"
    ]
    max_active = int(limits.get("max_active", len(active)))
    if len(active) > max_active:
        raise PoolRebuildError("max_active exceeded")

    for image in active:
        if any(
            key in image
            for key in ("embedding", "embeddings", "image_bytes")
        ):
            raise PoolRebuildError(
                "Embeddings or image bytes are forbidden"
            )
        if not image.get("path"):
            raise PoolRebuildError("Active image path is required")
        image["pool_rank"] = 0

    active.sort(
        key=lambda item: (
            -float(item.get("pool_utility_score", 0.0)),
            str(item["path"]),
        )
    )
    for rank, image in enumerate(active, 1):
        image["pool_rank"] = rank
        image["approved_at"] = image.get("approved_at") or _now()

    new_images = [
        dict(image)
        for image in images
        if image.get("status") == "new"
    ]
    all_images = active + new_images
    payload = {
        "schema_version": 1,
        "pool_type": pool_type,
        "updated_at": _now(),
        "selection_fingerprint": _fingerprint(
            all_images,
            model_fingerprint,
            preprocessing_fingerprint,
        ),
        "pool_build_id": hashlib.sha256(
            os.urandom(16)
        ).hexdigest()[:16],
        "rank_digits": max(1, len(str(max(1, len(active))))),
        "limits": dict(limits),
        "images": all_images,
        "model_fingerprint": model_fingerprint,
        "preprocessing_fingerprint": preprocessing_fingerprint,
    }
    if slug is not None:
        payload["slug"] = slug

    root.mkdir(parents=True, exist_ok=True)
    target = root / "selection.json"
    fd, temporary = tempfile.mkstemp(
        prefix=".selection.",
        dir=root,
    )
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
    """
    Hält Referenzwerte nur im RAM und baut sie bei Fingerprintwechsel neu auf.
    """

    def __init__(self):
        """Initialisiert einen leeren flüchtigen Referenzcache."""
        self.fingerprint: str | None = None
        self.values: dict = {}

    def get_or_rebuild(self, fingerprint: str, builder):
        """
        Liefert den Cache oder erstellt ihn bei geändertem Fingerprint neu.
        """
        if self.fingerprint != fingerprint:
            self.values = builder()
            self.fingerprint = fingerprint
        return self.values
