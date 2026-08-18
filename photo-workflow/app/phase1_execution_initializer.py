"""Initialize persisted Phase-1 analysis plans and WorkUnit states safely."""
from __future__ import annotations
from typing import Any, Iterable
from app.execution_plan import WorkUnitPlan
from app.phase1_analysis_plan import Phase1AnalysisPlanError, Phase1AnalysisPlanStore
from app.workunit_state import WorkUnitStateStore

class Phase1ExecutionInitializationError(ValueError):
    """Raised when rows and WorkUnits cannot form one safe execution plan."""

def initialize_execution_plan(*, batch_id: str, rows: list[dict[str, Any]], workunits: Iterable[WorkUnitPlan], config_fingerprint: str, analysis_plans: Phase1AnalysisPlanStore, workunit_states: WorkUnitStateStore) -> dict[str, Any]:
    """Persist a new plan once and initialize all of its WorkUnit states idempotently."""
    batch_workunits = tuple(unit for unit in workunits if unit.batch_id == batch_id)
    if not batch_workunits:
        raise Phase1ExecutionInitializationError("batch has no workunits")
    if any(unit.batch_id != batch_id for unit in batch_workunits):
        raise Phase1ExecutionInitializationError("workunit batch mismatch")
    workunit_records = [{"workunit_id": unit.workunit_id, "image_names": list(unit.image_names)} for unit in batch_workunits]
    existing = analysis_plans.load(batch_id)
    if existing is None:
        try:
            record = analysis_plans.write(batch_id=batch_id, rows=rows, workunits=workunit_records, config_fingerprint=config_fingerprint)
        except Phase1AnalysisPlanError as exc:
            raise Phase1ExecutionInitializationError(str(exc)) from exc
    else:
        if existing["config_fingerprint"] != config_fingerprint:
            raise Phase1ExecutionInitializationError("existing analysis plan config fingerprint differs")
        record = existing
    for unit in batch_workunits:
        workunit_states.initialize(batch_id=batch_id, workunit_id=unit.workunit_id, image_names=unit.image_names, config_fingerprint=config_fingerprint)
    return record
