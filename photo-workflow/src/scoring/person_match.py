"""Known-Person-Match (Spec 4.5, G4–G6)."""
from pathlib import Path

def count_known_person_matches(image_path: Path, reference_dir: Path) -> int:
    if not reference_dir.exists():
        return 0
    return 0

def validate_known_person_match_count(meta: dict) -> bool:
    count = meta.get("known_person_match_count")
    if count is None:
        return True
    return isinstance(count, int) and count >= 0
