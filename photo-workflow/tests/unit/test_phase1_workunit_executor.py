"""
Skript: tests/unit/test_phase1_workunit_executor.py
Zweck: Testet den kanonischen Review-/Rejected-Ordnervertrag.
Version: 1.0.0

Änderungsprotokoll:
  2026-08-22 | C1.2.3 | Kanonische Review-/Rejected-Ordnernamen ohne Unterstrich vereinheitlicht.
"""

from app.phase1_workunit_executor import execute_next_image

def _row(execution=None):
    return {"file": "a.jpg", "family_tags": ["family:test"], "family_regions": [], "execution": execution or {"target_relative_path": "Review/a.jpg", "moved": False, "family_metadata_written": False, "culling_metadata_written": False}}

def _workunit(state="pending", index=0):
    return {"workunit_id": "wu-1", "state": state, "next_image_index": index, "image_names": ["a.jpg"]}

def _run(tmp_path, row, workunit=None, culling=(True, "written")):
    updates, transitions, moved = [], [], []
    def move(source, target):
        source.rename(target); moved.append(target)
    result = execute_next_image(root=tmp_path, batch_id="batch-1", workunit=workunit or _workunit(), plan_rows=[row], cfg={}, update_execution=lambda **kwargs: updates.append(kwargs), transition=lambda **kwargs: transitions.append(kwargs), move_file=move, write_family=lambda *_: (True, "ok"), write_culling=lambda *_: culling)
    return result, updates, transitions, moved

def test_executes_and_persists_real_contracts(tmp_path):
    (tmp_path / "a.jpg").write_text("image")
    result, updates, transitions, moved = _run(tmp_path, _row())
    assert result.state == "completed"
    assert moved == [tmp_path / "Review/a.jpg"]
    assert updates == [{"batch_id": "batch-1", "file_name": "a.jpg", "moved": True}, {"batch_id": "batch-1", "file_name": "a.jpg", "family_metadata_written": True}, {"batch_id": "batch-1", "file_name": "a.jpg", "culling_metadata_written": True}]
    assert transitions[0]["new_state"] == "in_progress"
    assert transitions[-1]["new_state"] == "completed"

def test_resumes_after_persisted_move(tmp_path):
    target = tmp_path / "Review/a.jpg"; target.parent.mkdir(); target.write_text("image")
    result, updates, _, moved = _run(tmp_path, _row({"target_relative_path": "Review/a.jpg", "moved": True, "family_metadata_written": False, "culling_metadata_written": False}), _workunit("in_progress"))
    assert result.state == "completed"
    assert moved == []
    assert updates[0]["family_metadata_written"] is True

def test_failure_marks_workunit_failed_without_advancing(tmp_path):
    (tmp_path / "a.jpg").write_text("image")
    result, updates, transitions, _ = _run(tmp_path, _row(), culling=(False, "exiftool_missing"))
    assert result.message == "culling_metadata:exiftool_missing"
    assert updates[-1]["family_metadata_written"] is True
    assert transitions[-1] == {"batch_id": "batch-1", "workunit_id": "wu-1", "new_state": "failed", "next_image_index": 0, "reason": "culling_metadata:exiftool_missing"}
