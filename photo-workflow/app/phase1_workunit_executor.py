"""Resumable executor for one persisted Phase-1 WorkUnit image."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

@dataclass(frozen=True)
class ExecutionResult:
    state: str
    image_index: int
    message: str = ""

UpdateExecution = Callable[..., dict[str, Any]]
Transition = Callable[..., dict[str, Any]]
MoveFile = Callable[[Path, Path], None]
WriteFamily = Callable[[Path, list[str], dict[str, Any], list[dict[str, Any]]], tuple[bool, str]]
WriteCulling = Callable[[Path, dict[str, Any], dict[str, Any]], tuple[bool, str]]

def _fail(transition: Transition, batch_id: str, workunit_id: str, index: int, message: str) -> ExecutionResult:
    transition(batch_id=batch_id, workunit_id=workunit_id, new_state="failed", next_image_index=index, reason=message)
    return ExecutionResult("failed", index, message)

def execute_next_image(*, root: str | Path, batch_id: str, workunit: dict[str, Any], plan_rows: list[dict[str, Any]], cfg: dict[str, Any], update_execution: UpdateExecution, transition: Transition, move_file: MoveFile, write_family: WriteFamily, write_culling: WriteCulling) -> ExecutionResult:
    """Execute one image and persist every completed substep through store callbacks."""
    workunit_id = workunit["workunit_id"]
    index = int(workunit["next_image_index"])
    image_names = workunit["image_names"]
    state = workunit["state"]
    if state == "completed":
        return ExecutionResult("completed", index)
    if index >= len(image_names):
        transition(batch_id=batch_id, workunit_id=workunit_id, new_state="completed", next_image_index=index)
        return ExecutionResult("completed", index)
    if state in {"pending", "paused", "failed"}:
        transition(batch_id=batch_id, workunit_id=workunit_id, new_state="in_progress", next_image_index=index)
    file_name = image_names[index]
    row = next((candidate for candidate in plan_rows if candidate["file"] == file_name), None)
    if row is None:
        return _fail(transition, batch_id, workunit_id, index, "analysis_plan_row_missing")
    execution = row["execution"]
    root_path = Path(root)
    source = root_path / file_name
    target = root_path / execution["target_relative_path"]
    if not execution["moved"]:
        if source != target and source.exists() and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            move_file(source, target)
        elif source != target and source.exists() and target.exists():
            return _fail(transition, batch_id, workunit_id, index, "target_collision")
        elif source != target and not source.exists() and not target.exists():
            return _fail(transition, batch_id, workunit_id, index, "source_and_target_missing")
        update_execution(batch_id=batch_id, file_name=file_name, moved=True)
        execution = dict(execution, moved=True)
    if not execution["family_metadata_written"]:
        ok, status = write_family(target, row.get("family_tags", []), cfg, row.get("family_regions", []))
        if not ok:
            return _fail(transition, batch_id, workunit_id, index, f"family_metadata:{status}")
        update_execution(batch_id=batch_id, file_name=file_name, family_metadata_written=True)
        execution = dict(execution, family_metadata_written=True)
    if not execution["culling_metadata_written"]:
        ok, status = write_culling(target, row, cfg)
        if not ok:
            return _fail(transition, batch_id, workunit_id, index, f"culling_metadata:{status}")
        update_execution(batch_id=batch_id, file_name=file_name, culling_metadata_written=True)
    next_index = index + 1
    next_state = "completed" if next_index == len(image_names) else "in_progress"
    transition(batch_id=batch_id, workunit_id=workunit_id, new_state=next_state, next_image_index=next_index)
    return ExecutionResult(next_state, index)
