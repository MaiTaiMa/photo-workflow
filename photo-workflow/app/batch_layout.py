"""
Skript: app/batch_layout.py
Zweck: Verwaltet die kanonische Batch-Struktur und JPG-/ARW-Paarungen.
Autor: MaiTaiMa
Erstellt: 2026-08-08
Version: 1.1
Requires: Python 3.11

Änderungsprotokoll:
  2026-08-08 | 1.1 | AP22.2 Header, Kommentare und Formatierung ergänzt
"""

from __future__ import annotations

# === Standardbibliothek ===
# Zweck: Beschreibt Paarungsbefunde und verarbeitet Batchpfade.
# Eingabe: Batch-Ordner mit Hauptordner, ARW, Review und Rejected.
# Ausgabe: Kanonische Pfade oder blockierende Paarungsfehler.
from dataclasses import dataclass
from pathlib import Path


# === Dateitypen und Ordner ===
# Zweck: Definiert die im Batchvertrag zugelassenen Bildendungen.
# Wirkung: Andere Endungen werden von der aktiven JPG-/ARW-Prüfung ignoriert.
JPG_EXTENSIONS = {".jpg", ".jpeg"}
ARW_EXTENSIONS = {".arw"}
CANONICAL_DIRS = ("ARW", "SAVE", "Review", "Rejected")


@dataclass(frozen=True)
class PairingIssue:
    """
    Beschreibt eine unklare oder fehlende JPG-/ARW-Zuordnung.

    Mehrdeutige oder ungeschützte ARWs blockieren die weitere Phase.
    Die Pfade bleiben relativ zum geprüften Batch nachvollziehbar.
    """

    kind: str
    basename: str
    jpgs: tuple[str, ...] = ()
    arws: tuple[str, ...] = ()


def ensure_layout(batch: str | Path) -> dict[str, Path]:
    """
    Legt die vier kanonischen Batch-Unterordner an.

    Die Funktion verändert keine Bilddateien.
    Sie stellt nur die im Batchvertrag erforderlichen Zielordner bereit.
    """
    root = Path(batch)
    result = {}
    for name in CANONICAL_DIRS:
        path = root / name
        path.mkdir(parents=True, exist_ok=True)
        result[name] = path
    return result


def _basename(path: Path) -> str:
    """
    Normalisiert den Dateibasename für eine case-insensitive Paarung.

    Die Dateiendung wird durch Path.stem entfernt.
    Nur der normalisierte Stammname wird verglichen.
    """
    return path.stem.casefold()


def active_images(batch: str | Path) -> list[Path]:
    """
    Listet ausschließlich aktive JPGs im Batch-Hauptordner.

    JPGs in Review oder Rejected gelten nicht als aktiv.
    Dadurch wird die ARW-Schutzentscheidung nachvollziehbar begrenzt.
    """
    root = Path(batch)
    return sorted(
        path
        for path in root.iterdir()
        if path.is_file() and path.suffix.casefold() in JPG_EXTENSIONS
    )


def arw_files(batch: str | Path) -> list[Path]:
    """
    Listet ARW-Dateien unterhalb des kanonischen ARW-Ordners.

    Nur reguläre ARW-Dateien werden berücksichtigt.
    Symlinkdateien werden nicht als schützbare Originale akzeptiert.
    """
    root = Path(batch) / "ARW"
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and not path.is_symlink()
        and path.suffix.casefold() in ARW_EXTENSIONS
    )


def validate_pairings(batch: str | Path) -> list[PairingIssue]:
    """
    Prüft aktive JPGs und ARWs auf eindeutige Basename-Paarungen.

    Mehrere aktive JPGs, ungeschützte ARWs und mehrere ARWs je Basename.
    werden als blockierende PairingIssue-Objekte zurückgegeben.
    """
    root = Path(batch)
    jpg_by_name: dict[str, list[Path]] = {}
    arw_by_name: dict[str, list[Path]] = {}
    for path in active_images(root):
        jpg_by_name.setdefault(_basename(path), []).append(path)
    for path in arw_files(root):
        arw_by_name.setdefault(_basename(path), []).append(path)

    issues = []
    for name in sorted(set(jpg_by_name) | set(arw_by_name)):
        jpgs = jpg_by_name.get(name, [])
        arws = arw_by_name.get(name, [])
        if len(jpgs) > 1:
            issues.append(PairingIssue(
                "multiple_active_jpg",
                name,
                tuple(str(path) for path in jpgs),
                tuple(str(path) for path in arws),
            ))
        elif not jpgs and arws:
            issues.append(PairingIssue(
                "unprotected_arw",
                name,
                (),
                tuple(str(path) for path in arws),
            ))
        elif len(arws) > 1:
            issues.append(PairingIssue(
                "multiple_arw",
                name,
                tuple(str(path) for path in jpgs),
                tuple(str(path) for path in arws),
            ))
    return issues


def assert_review_state_valid(batch: str | Path) -> None:
    """
    Erzwingt einen widerspruchsfreien Review-Zustand vor Folgephasen.

    Jeder Pairing-Befund wird als `review_state_invalid` gemeldet.
    In diesem Zustand darf keine ARW-Aktion ausgeführt werden.
    """
    issues = validate_pairings(batch)
    if issues:
        details = ", ".join(
            f"{issue.kind}:{issue.basename}" for issue in issues
        )
        raise ValueError(f"review_state_invalid: {details}")
