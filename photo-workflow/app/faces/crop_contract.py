"""
Skript: app/faces/crop_contract.py
Zweck: Validiert und speichert neue Face-Crops im erlaubten Poolbereich.
Autor: MaiTaiMa
Erstellt: 2026-08-08
Version: 1.2
Requires: Python 3.11, Pillow

Änderungsprotokoll:
  2026-08-08 | 1.2 | AP22 Face-Crop-Vertrag nach 98AP formatiert
"""

from __future__ import annotations

# === Standardbibliothek ===
# Zweck: Prüft sichere Pfade und Bounding-Boxen für Face-Crops.
# Eingabe: Bildpfad, Zielordner, Slug, Dateiname und Box.
# Ausgabe: Manuell aktivierbarer Crop unter new_faces.
from pathlib import Path


class CropContractError(ValueError):
    """Beschreibt einen Verstoß gegen die Face-Crop-Poolgrenzen."""


def validate_box(box: dict, width: int, height: int) -> None:
    """
    Prüft eine Bounding-Box gegen die Bildgrenzen.

    Nur vollständig innerhalb des Bildes liegende, nichtleere Boxen sind erlaubt.
    """
    required = {"left", "top", "right", "bottom"}
    if required - box.keys():
        raise CropContractError("Bounding box is incomplete")

    left = int(box["left"])
    top = int(box["top"])
    right = int(box["right"])
    bottom = int(box["bottom"])
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise CropContractError("Bounding box is outside image")
    if min(right - left, bottom - top) < 1:
        raise CropContractError("Face crop is empty")


def save_new_face_crop(
    source: str | Path,
    destination_root: str | Path,
    *,
    slug: str,
    filename: str,
    box: dict,
) -> Path:
    """
    Speichert einen neuen Face-Crop ausschließlich unter `<slug>/new_faces`.

    Pfadtraversal, vorhandene Ziele und ungültige Bounding-Boxen blockieren.
    """
    source_path = Path(source)
    root = Path(destination_root)
    if Path(filename).name != filename or Path(slug).name != slug:
        raise CropContractError("Unsafe crop filename or slug")

    target_dir = root / slug / "new_faces"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / filename
    if target.exists():
        raise CropContractError(f"Crop already exists: {target}")

    try:
        from PIL import Image

        with Image.open(source_path) as image:
            validate_box(box, image.width, image.height)
            crop = image.crop(
                (
                    box["left"],
                    box["top"],
                    box["right"],
                    box["bottom"],
                )
            )
            crop.save(target)
    except Exception as exc:
        if target.exists():
            target.unlink()
        if isinstance(exc, CropContractError):
            raise
        raise CropContractError(str(exc)) from exc

    return target
