# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/path_security.py
# PURPOSE:     Prüft kanonische Workflow-, Publish- und Mountpfade.
# AUTHOR:      Matzethias
# DATE:        2026-08-08
# VERSION:     1.1
# REQUIRES:    Python 3.11
# CHANGES:
#   2026-08-08 | 1.1 | AP22.1 Header, Kommentare und Formatierung ergänzt
# =============================================================================


from __future__ import annotations

# === Standardbibliothek ===
# Zweck: Prüft Dateisystemgeräte und verarbeitet plattformunabhängige Pfade.
# Eingabe: Erlaubte Wurzeln, Zielpfade und Sicherheitsoptionen.
# Ausgabe: Kanonische Pfade oder ein blockierender Sicherheitsfehler.
import os
from pathlib import Path


class PathSecurityError(ValueError):
    """
    Beschreibt einen Verstoß gegen eine erlaubte Pfadgrenze.

    Der Fehler blockiert den betroffenen Datei- oder Publish-Schritt.
    Originale und externe Pfade bleiben dadurch unangetastet.
    """


def canonical(path: str | Path) -> Path:
    """
    Erzeugt den kanonischen Pfad ohne eine fehlende Datei anzulegen.

    Benutzerpfade werden expandiert und symbolische Verweise aufgelöst.
    Der Rückgabewert dient ausschließlich nachfolgender Sicherheitsprüfung.
    """
    return Path(path).expanduser().resolve(strict=False)


def _is_within(root: Path, target: Path) -> bool:
    """
    Prüft, ob der Zielpfad innerhalb der erlaubten Wurzel liegt.

    Der Vergleich erfolgt über relative Pfade und nicht über Zeichenketten.
    Dadurch werden Präfixverwechslungen und `..`-Traversal verhindert.
    """
    try:
        target.relative_to(root)
        return True
    except ValueError:
        return False


def _has_symlink_component(path: Path, stop: Path) -> bool:
    """
    Sucht zwischen Ziel und Wurzel nach symbolischen Pfadkomponenten.

    Symlinks werden standardmäßig blockiert, auch wenn das aufgelöste Ziel
    formal innerhalb der erlaubten Wurzel liegt.
    """
    current = path
    while current != stop and current != current.parent:
        if current.is_symlink():
            return True
        current = current.parent
    return False


def ensure_within(
    root: str | Path,
    target: str | Path,
    *,
    allow_missing: bool = True,
    reject_symlinks: bool = True,
    require_same_device: bool = False,
) -> Path:
    """
    Validiert einen Pfad gegen Wurzel, Symlink- und Mountregeln.

    Die kanonische Zielprüfung blockiert externe Pfade und Traversal.
    Optionale Existenz-, Symlink- und Dateisystemprüfungen verschärfen die Grenze.
    """
    root_path = canonical(root)
    target_path = canonical(target)
    if not _is_within(root_path, target_path):
        raise PathSecurityError(f"Path escapes allowed root: {target}")
    if reject_symlinks and _has_symlink_component(Path(target), Path(root)):
        raise PathSecurityError(f"Symlink component is not allowed: {target}")
    if not allow_missing and not target_path.exists():
        raise PathSecurityError(f"Path does not exist: {target}")
    if require_same_device and root_path.exists() and target_path.exists():
        root_device = os.stat(root_path).st_dev
        target_device = os.stat(target_path).st_dev
        if root_device != target_device:
            raise PathSecurityError(
                f"Mount/device differs from allowed root: {target}"
            )
    return target_path


def validate_publish_target(config: dict, target: str | Path) -> Path:
    """
    Validiert ein PHASE3-Ziel unterhalb von `paths.publish_root`.

    Der Publish-Pfad ist die einzige erlaubte Ausnahme zur Workflow-Wurzel.
    Symlinks und abweichende Dateisystemgeräte werden dabei blockiert.
    """
    paths = config.get("paths", {})
    root = paths.get("publish_root")
    if not root:
        raise PathSecurityError("paths.publish_root is required for publication")
    return ensure_within(
        root,
        target,
        reject_symlinks=True,
        require_same_device=True,
    )