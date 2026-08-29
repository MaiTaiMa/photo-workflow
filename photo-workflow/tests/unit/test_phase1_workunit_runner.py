# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_phase1_workunit_runner.py
# PURPOSE:     Testet den kanonischen Review-/Rejected-Ordnervertrag.
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   2026-08-22 | C1.2.3 | Kanonische Review-/Rejected-Ordnernamen ohne Unterstrich vereinheitlicht.
# =============================================================================


from app.phase1_analysis_plan import Phase1AnalysisPlanStore
from app.phase1_workunit_runner import Phase1WorkUnitRunner
from app.workunit_state import WorkUnitStateStore


def test_runner_binds_persisted_stores_and_executes_one_image(tmp_path):
    batch_id = "batch-1"
    plans = Phase1AnalysisPlanStore(tmp_path / "plans", "test")
    states = WorkUnitStateStore(tmp_path / "states", "test")
    row = {"file": "a.jpg", "family_tags": ["family:test"], "family_regions": [], "execution": {"target_relative_path": "Review/a.jpg", "moved": False, "family_metadata_written": False, "culling_metadata_written": False}}
    plans.write(batch_id=batch_id, rows=[row], workunits=[{"workunit_id": "wu-1", "image_names": ["a.jpg"]}], config_fingerprint="cfg")
    states.initialize(batch_id=batch_id, workunit_id="wu-1", image_names=("a.jpg",), config_fingerprint="cfg")
    (tmp_path / "a.jpg").write_text("image")
    runner = Phase1WorkUnitRunner(plans, states, family_writer=lambda *_: (True, "ok"), culling_writer=lambda *_: (True, "written"))
    result = runner.run_next(root=tmp_path, batch_id=batch_id, cfg={})
    assert result is not None and result.state == "completed"
    assert (tmp_path / "Review/a.jpg").exists()
    assert plans.load(batch_id)["rows"][0]["execution"] == {"target_relative_path": "Review/a.jpg", "moved": True, "family_metadata_written": True, "culling_metadata_written": True}
    assert states.load(batch_id, "wu-1")["state"] == "completed"


def test_runner_returns_none_without_open_workunit(tmp_path):
    runner = Phase1WorkUnitRunner(Phase1AnalysisPlanStore(tmp_path / "plans", "test"), WorkUnitStateStore(tmp_path / "states", "test"))
    assert runner.run_next(root=tmp_path, batch_id="batch-1", cfg={}) is None