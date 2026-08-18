"""Build safe, persisted Phase-1 analysis rows from final culling rows."""
from __future__ import annotations
from pathlib import Path
from typing import Any

class Phase1AnalysisBuildError(ValueError):
    """Raised when a final culling row cannot become a safe plan row."""

def _target_relative_path(file_name: str, decision: str, move_files: bool) -> str:
    if Path(file_name).name != file_name:
        raise Phase1AnalysisBuildError("analysis row file must be a plain name")
    if decision not in {"keep", "review", "reject"}:
        raise Phase1AnalysisBuildError("analysis row decision is invalid")
    if not move_files or decision == "keep":
        return file_name
    directory = "_Review" if decision == "review" else "_Rejected"
    return str(Path(directory) / file_name)

def build_persistable_analysis_rows(rows: list[dict[str, Any]], *, move_files: bool) -> list[dict[str, Any]]:
    """Return plan-safe copies of final culling rows without runtime-only fields."""
    if not isinstance(move_files, bool):
        raise Phase1AnalysisBuildError("move_files must be boolean")
    result: list[dict[str, Any]] = []
    seen_files: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise Phase1AnalysisBuildError("analysis row must be a mapping")
        file_name = row.get("file")
        if not isinstance(file_name, str):
            raise Phase1AnalysisBuildError("analysis row requires file")
        if file_name in seen_files:
            raise Phase1AnalysisBuildError("analysis row files must be unique")
        decision = row.get("decision")
        target = _target_relative_path(file_name, decision, move_files)
        family_tags = row.get("_family_tags", row.get("family_tags", []))
        family_regions = row.get("_family_regions", row.get("family_regions", []))
        if not isinstance(family_tags, list) or not isinstance(family_regions, list):
            raise Phase1AnalysisBuildError("family data must be lists")
        persisted = {key: value for key, value in row.items() if not str(key).startswith("_")}
        persisted["family_tags"] = family_tags
        persisted["family_regions"] = family_regions
        persisted["execution"] = {"target_relative_path": target, "moved": False, "family_metadata_written": False, "culling_metadata_written": False}
        result.append(persisted)
        seen_files.add(file_name)
    return result
