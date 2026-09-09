# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/faces/crop_contract.py
# PURPOSE:     Validiert und speichert neue Face-Crops im erlaubten Poolbereich.
# AUTHOR:      Matzethias
# DATE:        2026-08-08
# VERSION:     1.3
# REQUIRES:    Python 3.11, Pillow
# CHANGES:
#   2026-08-08 | 1.2 | AP22 Face-Crop-Vertrag nach 98AP formatiert
#   2026-09-09 | 1.3 | P6: Verschiebe-Helper not_used ergaenzt.
# =============================================================================


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



def check_new_faces_limit(destination_root: str | Path, slug: str, max_new_per_batch: int = 5) -> tuple[bool, int]:
    """
    Prueft ob max_new_per_batch fuer einen Slug erreicht ist.

    Returns (ok, current_count).
    """
    root = Path(destination_root)
    new_faces_dir = root / slug / "new_faces"

    if not new_faces_dir.exists():
        return True, 0

    current_count = len(list(new_faces_dir.glob("*.jpg"))) + len(list(new_faces_dir.glob("*.JPG"))) + len(list(new_faces_dir.glob("*.png")))

    if current_count >= max_new_per_batch:
        return False, current_count

    return True, current_count

def save_new_face_crop(
    source: str | Path,
    destination_root: str | Path,
    *,
    slug: str,
    filename: str,
    box: dict,
    max_new_per_batch: int = 5,
) -> Path:
    """
    Speichert einen neuen Face-Crop ausschließlich unter `<slug>/new_faces`.

    Pfadtraversal, vorhandene Ziele, ungültige Bounding-Boxen und max_new_per_batch blockieren.
    """
    source_path = Path(source)
    root = Path(destination_root)
    if Path(filename).name != filename or Path(slug).name != slug:
        raise CropContractError("Unsafe crop filename or slug")

    # max_new_per_batch Pruefung
    ok, count = check_new_faces_limit(root, slug, max_new_per_batch)
    if not ok:
        raise CropContractError(f"max_new_per_batch ({max_new_per_batch}) reached for {slug}: {count} crops")

    target_dir = root / slug / "new_faces"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / filename
    if target.exists():
        raise CropContractError(f"Crop already exists: {target}")

    try:
        from PIL import Image, ImageOps

        with Image.open(source_path) as _opened:
            image = ImageOps.exif_transpose(_opened)
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


# === not_used-Verschiebung (P6) ===
# Zweck: Entfernt nicht benoetigte Crops nachvollziehbar aus new_faces.
# Eingabe: Pfad zu einem Crop unter <person>/new_faces.
# Ausgabe: Zielpfad unter <person>/not_used; es wird nie geloescht.


def move_face_crop_to_not_used(crop_path: str | Path) -> Path:
    """Verschiebt einen nicht benötigten Crop von new_faces nach not_used.

    Blockiert bei fehlender oder unsicherer Quelle, falschem Ordner und
    vorhandenem Ziel; es wird niemals überschrieben oder gelöscht.
    """
    source = Path(crop_path)
    if source.parent.name != "new_faces":
        raise CropContractError(f"crop is not inside new_faces: {source}")
    if not source.is_file() or source.is_symlink():
        raise CropContractError(f"crop is missing or unsafe: {source}")
    target_dir = source.parent.parent / "not_used"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    if target.exists():
        raise CropContractError(f"not_used target already exists: {target}")
    source.rename(target)
    return target
