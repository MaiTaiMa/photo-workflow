# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/faces/reference_pool.py
# PURPOSE:     Lädt verifizierte, aktive Referenzbilder ohne Embedding-Persistenz.
# AUTHOR:      Matzethias
# DATE:        2026-08-08
# VERSION:     1.2
# REQUIRES:    Python 3.11
# CHANGES:
#   2026-08-08 | 1.2 | AP22 Fingerprint-Prüfung an Pool-Rebuild angeglichen
# =============================================================================


from __future__ import annotations

# === Standardbibliothek ===
# Zweck: Validiert JSON-Verträge und berechnet Pool-Fingerprints.
# Eingabe: selection.json und Referenzpool-Verzeichnis.
# Ausgabe: Verifizierte Auswahl und sichere aktive Bildpfade.
import hashlib
import json
from pathlib import Path


class ReferencePoolError(ValueError):
    """Beschreibt einen Verstoß gegen den Referenzpool-Vertrag."""


def _fingerprint(
    images: list[dict],
    model_fingerprint: str = "",
    preprocessing_fingerprint: str = "",
) -> str:
    """Berechnet den kanonischen Fingerprint eines Referenzpools."""
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


def load_active_references(
    pool_root: str | Path,
    *,
    pool_type: str,
    slug: str | None = None,
) -> tuple[dict, list[Path]]:
    """
    Lädt und validiert aktive Referenzbilder eines Auswahlpools.

    Embeddings und Bildbytes werden aus selection.json ausgeschlossen.
    Die zurückgegebenen Bildpfade sind ausschließlich für RAM-Verarbeitung.
    """
    root = Path(pool_root)
    selection_path = root / "selection.json"
    if not selection_path.exists():
        raise ReferencePoolError(f"Missing selection.json: {root}")

    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "pool_type",
        "updated_at",
        "selection_fingerprint",
        "pool_build_id",
        "rank_digits",
        "limits",
        "images",
    }
    missing = required - selection.keys()
    if missing:
        raise ReferencePoolError(
            f"Missing selection fields: {sorted(missing)}"
        )

    if selection["pool_type"] != pool_type:
        raise ReferencePoolError("Reference pool type mismatch")
    if pool_type == "face" and selection.get("slug") != slug:
        raise ReferencePoolError("Face pool slug mismatch")

    images = selection["images"]
    if not isinstance(images, list):
        raise ReferencePoolError("selection.images must be a list")

    for entry in images:
        if any(
            key in entry
            for key in ("embedding", "embeddings", "image_bytes")
        ):
            raise ReferencePoolError(
                "Binary data or embeddings in selection.json"
            )

    active = []
    for entry in images:
        if entry.get("status") != "active":
            continue
        relative = Path(entry["path"])
        path = root / "reference" / relative.name
        if not path.exists() or path.is_symlink():
            raise ReferencePoolError(
                f"Active reference missing or unsafe: {path}"
            )
        active.append(path)

    expected = _fingerprint(
        images,
        selection.get("model_fingerprint", ""),
        selection.get("preprocessing_fingerprint", ""),
    )
    if selection["selection_fingerprint"] != expected:
        raise ReferencePoolError("selection_fingerprint mismatch")

    return selection, active