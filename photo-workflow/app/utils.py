"""
Shared utility functions for photo-workflow.
"""

from pathlib import Path
from typing import List, Set

# Supported image extensions (case-insensitive)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}


def top_level_images(folder: Path) -> List[Path]:
    """
    Returns supported image files directly in folder (no subfolders).
    Sorted by name for reproducible ordering.
    
    Excludes:
      - Symlinks
      - Hidden files (starting with '.')
      - Non-image files
    """
    if not folder.is_dir():
        return []
    
    return sorted(
        (
            path
            for path in folder.iterdir()
            if path.is_file()
            and not path.is_symlink()
            and not path.name.startswith('.')
            and path.suffix.lower() in IMAGE_EXTENSIONS
        ),
        key=lambda path: path.name.lower(),
    )


def top_level_jpgs(folder: Path) -> List[Path]:
    """
    Returns only .JPG/.jpeg files directly in folder (no subfolders).
    Sorted by name for reproducible ordering.
    
    Excludes:
      - Symlinks
      - Hidden files (starting with '.')
      - Non-JPG files
    """
    if not folder.is_dir():
        return []
    
    return sorted(
        (
            path
            for path in folder.iterdir()
            if path.is_file()
            and not path.is_symlink()
            and not path.name.startswith('.')
            and path.suffix.lower() in {".jpg", ".jpeg"}
        ),
        key=lambda path: path.name.lower(),
    )


def is_image_file(path: Path) -> bool:
    """Check if path is a supported image file."""
    return path.is_file() and not path.is_symlink() and path.suffix.lower() in IMAGE_EXTENSIONS


def is_jpg_file(path: Path) -> bool:
    """Check if path is a .JPG file."""
    return path.is_file() and not path.is_symlink() and path.suffix.lower() in {".jpg", ".jpeg"}