from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageStat


@dataclass(frozen=True)
class TechnicalScore:
    base_score: float | None
    sharp_score: float | None
    exposure_score: float | None
    aesth_score: float | None
    status: str
    error: str | None = None


def _normal(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def score_image(path: str | Path) -> TechnicalScore:
    try:
        with Image.open(path) as source:
            image = source.convert("L")
            values = np.asarray(image, dtype=np.float32) / 255.0
        if values.size == 0:
            raise ValueError("empty image")
        variance = float(np.var(values))
        sharp = _normal(variance * 12.0)
        clipped = float(np.mean((values <= 0.01) | (values >= 0.99)))
        exposure = _normal(1.0 - clipped * 2.0)
        mean = float(np.mean(values))
        balance = _normal(1.0 - abs(mean - 0.5) * 1.8)
        contrast = _normal(float(np.std(values)) * 3.0)
        aesth = _normal((balance + contrast) / 2.0)
        base = _normal(0.36 * sharp + 0.36 * aesth + 0.18 * exposure + 0.10 * balance)
        return TechnicalScore(base, sharp, exposure, aesth, "ok")
    except Exception as exc:
        return TechnicalScore(None, None, None, None, "analysis_error", str(exc))
