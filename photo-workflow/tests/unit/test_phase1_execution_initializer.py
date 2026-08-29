# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_phase1_execution_initializer.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


import pytest
from app.execution_plan import WorkUnitPlan
from app.phase1_execution_initializer import Phase1ExecutionInitializationError, initialize_execution_plan
from app.phase1_analysis_plan import Phase1AnalysisPlanStore
from app.workunit_state import WorkUnitStateStore

def _row(name):
    return {"file": name, "decision": "keep", "family_tags": [], "family_regions": [], "execution": {"target_relative_path": name, "moved": False, "family_metadata_written": False, "culling_metadata_written": False}}

def test_writes_plan_and_initializes_states(tmp_path):
    plans = Phase1AnalysisPlanStore(tmp_path / "plans", "test")
    states = WorkUnitStateStore(tmp_path / "states", "test")
    units = [WorkUnitPlan("batch-1:wu-0001", "batch-1", 1, ("a.jpg",)), WorkUnitPlan("batch-1:wu-0002", "batch-1", 2, ("b.jpg",))]
    record = initialize_execution_plan(batch_id="batch-1", rows=[_row("a.jpg"), _row("b.jpg")], workunits=units, config_fingerprint="cfg", analysis_plans=plans, workunit_states=states)
    assert record["batch_id"] == "batch-1"
    assert states.load("batch-1", "batch-1:wu-0001")["state"] == "pending"
    assert states.load("batch-1", "batch-1:wu-0002")["image_names"] == ["b.jpg"]

def test_existing_plan_preserves_execution_progress(tmp_path):
    plans = Phase1AnalysisPlanStore(tmp_path / "plans", "test")
    states = WorkUnitStateStore(tmp_path / "states", "test")
    unit = WorkUnitPlan("batch-1:wu-0001", "batch-1", 1, ("a.jpg",))
    initialize_execution_plan(batch_id="batch-1", rows=[_row("a.jpg")], workunits=[unit], config_fingerprint="cfg", analysis_plans=plans, workunit_states=states)
    plans.update_execution(batch_id="batch-1", file_name="a.jpg", moved=True)
    initialize_execution_plan(batch_id="batch-1", rows=[_row("a.jpg")], workunits=[unit], config_fingerprint="cfg", analysis_plans=plans, workunit_states=states)
    assert plans.load("batch-1")["rows"][0]["execution"]["moved"] is True

def test_rejects_missing_batch_workunits(tmp_path):
    with pytest.raises(Phase1ExecutionInitializationError, match="no workunits"):
        initialize_execution_plan(batch_id="batch-1", rows=[], workunits=[], config_fingerprint="cfg", analysis_plans=Phase1AnalysisPlanStore(tmp_path / "plans", "test"), workunit_states=WorkUnitStateStore(tmp_path / "states", "test"))