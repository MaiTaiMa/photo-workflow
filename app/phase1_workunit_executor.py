"""Resumable executor for one Phase-1 WorkUnit image.

This module is intentionally not wired into ``photo_workflow.py``.  Its callers
provide persistence and filesystem callbacks so that integration remains an
explicit, separately reviewable step.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    image_index: int
    message: str = ""


UpdatePlan = Callable[[dict[str, Any]], None]
UpdateWorkUnit = Callable[[dict[str, Any]], None]
MoveFile = Callable[[Path, Path], None]
WriteFamily = Callable[[Path, list[str], dict[str, Any], list[dict[str, Any]]], tuple[bool, str]]
WriteCulling = Callable[[Path, dict[str, Any], dict[str, Any]], tuple[bool, str]]


def _target_path(root: Path, row: dict[str, Any]) -> Path:
    execution = row.get("execution") or {}
    return root / execution.get("target_path", row["file"])


def _record(execution: dict[str, Any], key: str, value: bool, status: str) -> dict[str, Any]:
    updated = dict(execution)
    updated[key] = value
    updated[f"{key}_status"] = status
    return updated


def execute_next_image(
    *,
    root: str | Path,
    workunit: dict[str, Any],
    plan_rows: list[dict[str, Any]],
    cfg: dict[str, Any],
    update_plan: UpdatePlan,
    update_workunit: UpdateWorkUnit,
    move_file: MoveFile,
    write_family: WriteFamily,
    write_culling: WriteCulling,
) -> ExecutionResult:
    """Execute at most one image and persist every successful substep.

    ``update_plan`` receives the complete updated row. ``update_workunit``
    receives a shallow copy of the WorkUnit. Both callbacks must persist
    atomically before returning.
    """
    state = workunit.get("state", "pending")
    index = int(workunit.get("next_image_index", 0))
    images = workunit.get("images", [])
    if state == "completed":
        return ExecutionResult("completed", index)
    if index >= len(images):
        completed = dict(workunit, state="completed")
        update_workunit(completed)
        return ExecutionResult("completed", index)

    image = images[index]
    row = next((item for item in plan_rows if item.get("file") == image), None)
    if row is None:
        return ExecutionResult("failed", index, "analysis_plan_row_missing")

    root_path = Path(root)
    source = root_path / image
    target = _target_path(root_path, row)
    execution = dict(row.get("execution") or {})

    if not execution.get("moved", False):
        if source == target:
            pass
        elif source.exists() and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            move_file(source, target)
        elif not source.exists() and target.exists():
            pass
        elif source.exists() and target.exists():
            return ExecutionResult("failed", index, "target_collision")
        else:
            return ExecutionResult("failed", index, "source_and_target_missing")
        execution = _record(execution, "moved", True, "ok")
        row = dict(row, execution=execution)
        update_plan(row)

    if not execution.get("family_metadata_written", False):
        ok, status = write_family(
            target,
            row.get("_family_tags", []),
            cfg,
            row.get("_family_regions", []),
        )
        if not ok:
            return ExecutionResult("failed", index, f"family_metadata:{status}")
        execution = _record(execution, "family_metadata_written", True, status)
        row = dict(row, execution=execution)
        update_plan(row)

    if not execution.get("culling_metadata_written", False):
        ok, status = write_culling(target, row, cfg)
        if not ok:
            return ExecutionResult("failed", index, f"culling_metadata:{status}")
        execution = _record(execution, "culling_metadata_written", True, status)
        row = dict(row, execution=execution)
        update_plan(row)

    next_workunit = dict(workunit, state="in_progress", next_image_index=index + 1)
    if index + 1 >= len(images):
        next_workunit["state"] = "completed"
    update_workunit(next_workunit)
    return ExecutionResult(next_workunit["state"], index)
