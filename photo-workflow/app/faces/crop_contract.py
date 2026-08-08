from __future__ import annotations

from pathlib import Path


class CropContractError(ValueError):
    """Raised when a face-crop operation violates pool boundaries."""


def validate_box(box: dict, width: int, height: int) -> None:
    required = {"left", "top", "right", "bottom"}
    if required - box.keys():
        raise CropContractError("Bounding box is incomplete")
    left, top = int(box["left"]), int(box["top"])
    right, bottom = int(box["right"]), int(box["bottom"])
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise CropContractError("Bounding box is outside image")
    if min(right - left, bottom - top) < 1:
        raise CropContractError("Face crop is empty")


def save_new_face_crop(source: str | Path, destination_root: str | Path,
                       *, slug: str, filename: str, box: dict) -> Path:
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
            image.crop((box["left"], box["top"], box["right"], box["bottom"])).save(target)
    except Exception as exc:
        if target.exists():
            target.unlink()
        if isinstance(exc, CropContractError):
            raise
        raise CropContractError(str(exc)) from exc
    return target
