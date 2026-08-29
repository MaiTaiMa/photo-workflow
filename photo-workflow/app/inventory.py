# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/inventory.py
# PURPOSE:     Erstellt stabile Batch-Inventare mit Dateigröße und SHA256-Hash.
# AUTHOR:      Matzethias
# DATE:        2026-08-08
# VERSION:     1.1
# REQUIRES:    Python 3.11
# CHANGES:
#   2026-08-08 | 1.1 | AP22.2 Header, Kommentare und Formatierung ergänzt
# =============================================================================


from __future__ import annotations

# === Standardbibliothek ===
# Zweck: Erzeugt Dateihashes, Inventarobjekte und atomare JSON-Dateien.
# Eingabe: Batch-Ordner, Warteintervall und Inventardaten.
# Ausgabe: Stabiles Inventar, Fingerprint oder gespeichertes JSON-Artefakt.
import hashlib
import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class InventoryEntry:
    """
    Beschreibt eine reguläre Datei im Batch-Inventar.

    Der relative Pfad bleibt batchbezogen.
    Größe, Änderungszeit und SHA256 dienen der Stabilitäts- und Integritätsprüfung.
    """

    relative_path: str
    size: int
    mtime_ns: int
    sha256: str


def _sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """
    Berechnet den SHA256-Hash einer Datei in begrenzten Speicherblöcken.

    Die Datei wird ausschließlich gelesen.
    Das Chunking verhindert, dass große Originale vollständig im RAM liegen.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def collect_inventory(root: str | Path) -> list[InventoryEntry]:
    """
    Sammelt deterministische Inventareinträge unterhalb eines Batch-Ordners.

    Symlinks und nichtreguläre Dateien werden ausgeschlossen.
    Jeder reguläre Eintrag erhält einen vollständigen Inhalts-Hash.
    """
    base = Path(root)
    entries = []
    for path in sorted(base.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        stat = path.stat()
        entries.append(
            InventoryEntry(
                relative_path=str(path.relative_to(base)),
                size=stat.st_size,
                mtime_ns=stat.st_mtime_ns,
                sha256=_sha256(path),
            )
        )
    return entries


def inventory_fingerprint(entries: list[InventoryEntry]) -> str:
    """
    Berechnet den SHA256-Fingerprint einer sortierten Inventarliste.

    Alle wesentlichen Dateifelder fließen in den Fingerprint ein.
    Der Rückgabewert ist für Manifest- und Stabilitätsnachweise bestimmt.
    """
    payload = "\n".join(
        f"{entry.relative_path}\0{entry.size}\0"
        f"{entry.mtime_ns}\0{entry.sha256}"
        for entry in entries
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def stable_inventory(
    root: str | Path,
    wait_seconds: float = 1.0,
) -> tuple[list[InventoryEntry], str]:
    """
    Erstellt zwei Inventare und bestätigt die Stabilität des Batch-Ordners.

    Eine Änderung zwischen den Aufnahmen blockiert die weitere Verarbeitung.
    Bei Erfolg werden das zweite Inventar und sein Fingerprint zurückgegeben.
    """
    first = collect_inventory(root)
    if wait_seconds > 0:
        time.sleep(wait_seconds)
    second = collect_inventory(root)
    if first != second:
        raise RuntimeError("Batch is not stable: inventory changed during observation")
    return second, inventory_fingerprint(second)


def write_inventory(
    path: str | Path,
    entries: list[InventoryEntry],
    fingerprint: str,
) -> None:
    """
    Schreibt ein Inventar atomar als JSON-Artefakt.

    Die temporäre Datei liegt im Zielordner.
    Nach Flush und fsync aktiviert os.replace den vollständigen Inventarstand.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    value = {
        "schema_version": 1,
        "producer_version": "ap22.2.2",
        "created_at": datetime.now(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        ),
        "entry_count": len(entries),
        "inventory_hash": fingerprint,
        "entries": [asdict(entry) for entry in entries],
    }
    fd, temporary = tempfile.mkstemp(
        prefix=f".{target.name}.",
        dir=target.parent,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)