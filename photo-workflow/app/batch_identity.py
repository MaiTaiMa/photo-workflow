# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/batch_identity.py
# PURPOSE:     Erzeugt stabile Fingerprints und unveränderliche Batch-IDs.
# AUTHOR:      Matzethias
# DATE:        2026-08-08
# VERSION:     1.1
# REQUIRES:    Python 3.11
# CHANGES:
#   2026-08-08 | 1.1 | AP22.1 Header, Kommentare und Formatierung ergänzt
# =============================================================================


from __future__ import annotations

# === Standardbibliothek ===
# Zweck: Hashes und rekursive Dateisysteminventare für Batches erzeugen.
# Eingabe: Ein physischer Batch-Ordner.
# Ausgabe: Achtstelliger Fingerprint oder zusammengesetzte batch_id.
import hashlib
from pathlib import Path


def _inventory(folder: Path) -> list[str]:
    """
    Erstellt deterministische Inventarzeilen für alle regulären Dateien.

    Symlinks werden aus Sicherheitsgründen ausgeschlossen.
    Pfad, Größe und Änderungszeit bilden die Eingabe für den Fingerprint.
    """
    rows = []
    for path in sorted(folder.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        stat = path.stat()
        rows.append(
            f"{path.relative_to(folder)}\0{stat.st_size}\0{stat.st_mtime_ns}"
        )
    return rows


def batch_fingerprint(folder: str | Path) -> str:
    """
    Berechnet den gekürzten SHA256-Fingerprint eines Batch-Inventars.

    Die Kürzung auf acht Hexzeichen entspricht dem Batch-ID-Vertrag.
    Der Ordnerinhalt wird nicht verändert und es werden keine Bildbytes gespeichert.
    """
    root = Path(folder)
    payload = "\n".join(_inventory(root)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:8]


def batch_id(folder: str | Path) -> str:
    """
    Erzeugt die unveränderliche Batch-ID aus Ordnername und Fingerprint.

    Das Format bleibt `source-folder-name+fingerprint(8)`.
    Die ID ist für Zustände, Manifeste und Phasenwechsel vorgesehen.
    """
    root = Path(folder)
    return f"{root.name}+{batch_fingerprint(root)}"