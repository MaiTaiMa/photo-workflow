from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


class MetadataError(ValueError):
    """Raised when metadata cannot be written or verified."""


def build_keywords(row: dict) -> list[str]:
    keywords = ["workflow:ai_cull", "decision:final"]
    decision = str(row.get("decision", "unknown")).lower()
    keywords.append(f"decision:{decision}")
    if row.get("manual_keep") is True:
        keywords.append("manual_keep:true")
    if row.get("series_id"):
        keywords.append(f"series:id:{row['series_id']}")
        keywords.append(f"series:rank:{int(row.get('series_rank', 1))}")
        keywords.append(f"series:best:{str(bool(row.get('series_best'))).lower()}")
    for person in row.get("detected_people", []) or []:
        keywords.append(f"person:{person}")
    if row.get("family_score") not in (None, ""):
        keywords.append("family:match:true")
    return sorted(set(keywords))


def write_and_readback(path: str | Path, row: dict, *, exiftool: str = "exiftool",
                       dry_run: bool = False) -> dict:
    target = Path(path)
    keywords = build_keywords(row)
    rating = int(row.get("star_rating", 0) or 0)
    expected = {"rating": rating, "keywords": keywords}
    if dry_run:
        return {"status": "disabled", "expected": expected, "verified": False}
    executable = shutil.which(exiftool)
    if executable is None:
        return {"status": "failed", "reason": "exiftool_missing", "verified": False}
    command = [executable, "-overwrite_original", f"-XMP:Rating={rating}"]
    command.extend(f"-XMP-dc:Subject+={keyword}" for keyword in keywords)
    command.extend(["-json", str(target)])
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        read = subprocess.run([exiftool, "-j", "-XMP:Rating", "-XMP-dc:Subject", str(target)],
                              check=True, capture_output=True, text=True)
        payload = json.loads(read.stdout or "[]")
        metadata = payload[0] if payload else {}
        actual_keywords = metadata.get("Subject", metadata.get("XMP-dc:Subject", []))
        if isinstance(actual_keywords, str):
            actual_keywords = [actual_keywords]
        verified = (int(metadata.get("Rating", metadata.get("XMP:Rating", -1))) == rating
                    and set(keywords).issubset(set(actual_keywords)))
        return {"status": "success" if verified else "failed", "expected": expected,
                "verified": verified}
    except (OSError, subprocess.CalledProcessError, ValueError, json.JSONDecodeError) as exc:
        return {"status": "failed", "reason": str(exc)[:200], "verified": False}
