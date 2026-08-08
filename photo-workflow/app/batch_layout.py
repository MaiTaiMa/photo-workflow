from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


JPG_EXTENSIONS = {".jpg", ".jpeg"}
ARW_EXTENSIONS = {".arw"}
CANONICAL_DIRS = ("ARW", "SAVE", "Review", "Rejected")


@dataclass(frozen=True)
class PairingIssue:
    kind: str
    basename: str
    jpgs: tuple[str, ...] = ()
    arws: tuple[str, ...] = ()


def ensure_layout(batch: str | Path) -> dict[str, Path]:
    root = Path(batch)
    result = {}
    for name in CANONICAL_DIRS:
        path = root / name
        path.mkdir(parents=True, exist_ok=True)
        result[name] = path
    return result


def _basename(path: Path) -> str:
    return path.stem.casefold()


def active_images(batch: str | Path) -> list[Path]:
    root = Path(batch)
    return sorted(p for p in root.iterdir() if p.is_file()
                  and p.suffix.casefold() in JPG_EXTENSIONS)


def arw_files(batch: str | Path) -> list[Path]:
    root = Path(batch) / "ARW"
    return sorted(p for p in root.rglob("*") if p.is_file()
                  and p.suffix.casefold() in ARW_EXTENSIONS)


def validate_pairings(batch: str | Path) -> list[PairingIssue]:
    root = Path(batch)
    jpg_by_name: dict[str, list[Path]] = {}
    arw_by_name: dict[str, list[Path]] = {}
    for path in active_images(root):
        jpg_by_name.setdefault(_basename(path), []).append(path)
    for path in arw_files(root):
        arw_by_name.setdefault(_basename(path), []).append(path)
    issues = []
    for name in sorted(set(jpg_by_name) | set(arw_by_name)):
        jpgs = jpg_by_name.get(name, [])
        arws = arw_by_name.get(name, [])
        if len(jpgs) > 1:
            issues.append(PairingIssue("multiple_active_jpg", name,
                                       tuple(str(p) for p in jpgs),
                                       tuple(str(p) for p in arws)))
        elif not jpgs and arws:
            issues.append(PairingIssue("unprotected_arw", name, (),
                                       tuple(str(p) for p in arws)))
        elif len(arws) > 1:
            issues.append(PairingIssue("multiple_arw", name,
                                       tuple(str(p) for p in jpgs),
                                       tuple(str(p) for p in arws)))
    return issues


def assert_review_state_valid(batch: str | Path) -> None:
    issues = validate_pairings(batch)
    if issues:
        details = ", ".join(f"{issue.kind}:{issue.basename}" for issue in issues)
        raise ValueError(f"review_state_invalid: {details}")
