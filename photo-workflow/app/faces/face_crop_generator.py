# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/faces/face_crop_generator.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-09-03
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from PIL import Image


class FaceCropError(ValueError):
    """Beschreibt einen ungültigen oder nicht erzeugbaren Face-Crop."""


def create_square_face_crop(
    image_path: str | Path,
    bounding_box: Mapping[str, Any],
    output_path: str | Path,
    *,
    target_size: int = 256,
    padding_ratio: float = 0.40,
) -> Path:
    """Create one padded square RGB JPEG crop atomically under new_faces."""
    source = Path(image_path)
    target = Path(output_path)
    if not source.is_file():
        raise FaceCropError(f"source image does not exist: {source}")
    if target_size < 32:
        raise FaceCropError("target_size must be at least 32")
    if not 0.0 <= padding_ratio <= 2.0:
        raise FaceCropError("padding_ratio must be between 0 and 2")
    _validate_box_shape(bounding_box)

    try:
        with Image.open(source) as image:
            image.load()
            width, height = image.size
            box = _validated_box(bounding_box, width, height)
            crop = _padded_square(image, box, padding_ratio)
            crop = crop.convert("RGB").resize(
                (target_size, target_size),
                Image.Resampling.LANCZOS,
            )
            _write_atomic_jpeg(crop, target)
    except FaceCropError:
        raise
    except Exception as error:
        raise FaceCropError(f"could not create face crop: {error}") from error
    return target


def _validate_box_shape(box: Mapping[str, Any]) -> None:
    if not isinstance(box, Mapping):
        raise FaceCropError("bounding_box must be a mapping")
    if set(box) != {"left", "top", "right", "bottom"}:
        raise FaceCropError(
            "bounding_box must contain exactly left, top, right, bottom"
        )
    if any(
        not isinstance(box[key], int) or isinstance(box[key], bool)
        for key in box
    ):
        raise FaceCropError("bounding_box coordinates must be integers")


def _validated_box(
    box: Mapping[str, int],
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    left, top, right, bottom = (
        box["left"], box["top"], box["right"], box["bottom"]
    )
    if left < 0 or top < 0 or right > width or bottom > height:
        raise FaceCropError("bounding_box lies outside the source image")
    if right <= left or bottom <= top:
        raise FaceCropError("bounding_box must have positive area")
    return left, top, right, bottom


def _padded_square(
    image: Image.Image,
    box: tuple[int, int, int, int],
    padding_ratio: float,
) -> Image.Image:
    left, top, right, bottom = box
    face_width = right - left
    face_height = bottom - top
    side = max(face_width, face_height) * (1.0 + padding_ratio)
    center_x = (left + right) / 2.0
    center_y = (top + bottom) / 2.0
    crop_left = int(round(center_x - side / 2.0))
    crop_top = int(round(center_y - side / 2.0))
    crop_right = crop_left + int(round(side))
    crop_bottom = crop_top + int(round(side))

    crop_size = max(crop_right - crop_left, crop_bottom - crop_top)
    crop = Image.new("RGB", (crop_size, crop_size), (0, 0, 0))
    source_left = max(0, crop_left)
    source_top = max(0, crop_top)
    source_right = min(image.width, crop_right)
    source_bottom = min(image.height, crop_bottom)
    if source_right <= source_left or source_bottom <= source_top:
        raise FaceCropError("padded crop has no intersection with source image")
    region = image.crop((source_left, source_top, source_right, source_bottom)).convert("RGB")
    paste_x = source_left - crop_left
    paste_y = source_top - crop_top
    crop.paste(region, (paste_x, paste_y))
    return crop


def _write_atomic_jpeg(image: Image.Image, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=target.parent,
        prefix=f".{target.stem}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        os.close(descriptor)
        image.save(temporary, format="JPEG", quality=95, optimize=True)
        temporary.replace(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
