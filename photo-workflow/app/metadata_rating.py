# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/metadata_rating.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


from __future__ import annotations

from pathlib import Path
import re
from typing import Optional

RATING_PATTERNS = [
    re.compile(r"<xmp:Rating>([0-5])</xmp:Rating>", re.IGNORECASE),
    re.compile(r'xmp:Rating="([0-5])"', re.IGNORECASE),
    re.compile(r'<Rating>([0-5])</Rating>', re.IGNORECASE),
    re.compile(r'Rating="([0-5])"', re.IGNORECASE),
]


def _extract_rating_from_text(text: str) -> Optional[float]:
    for pattern in RATING_PATTERNS:
        match = pattern.search(text)
        if match:
            return float(match.group(1))
    return None


def read_rating(image_path: str | Path) -> Optional[float]:
    path = Path(image_path)
    sidecars = [path.with_suffix(path.suffix + '.xmp'), path.with_suffix('.xmp')]
    for sidecar in sidecars:
        if sidecar.exists() and sidecar.is_file():
            try:
                text = sidecar.read_text(encoding='utf-8', errors='ignore')
                rating = _extract_rating_from_text(text)
                if rating is not None:
                    return rating
            except OSError:
                pass

    try:
        data = path.read_bytes()
        text = data.decode('utf-8', errors='ignore')
        rating = _extract_rating_from_text(text)
        if rating is not None:
            return rating
    except OSError:
        return None
    return None