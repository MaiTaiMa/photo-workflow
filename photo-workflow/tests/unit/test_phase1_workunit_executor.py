from app.phase1_workunit_executor import execute_next_image


def _row(execution=None):
    return {"file": "a.jpg", "_family_tags": ["family:test"], "_family_regions": [], "execution": execution or {"target_path": "_Review/a.jpg"}}


def _run(tmp_path, row, culling=(True, "written")):
    plans, units, moved = [], [], []
    def move(source, target):
        source.rename(target); moved.append(target)
    result = execute_next_image(root=tmp_path, workunit={"state": "pending", "next_image_index": 0, "images": ["a.jpg"]}, plan_rows=[row], cfg={}, update_plan=plans.append, update_workunit=units.append, move_file=move, write_family=lambda *_: (True, "ok"), write_culling=lambda *_: culling)
    return result, plans, units, moved


def test_executes_one_image_and_completes_workunit(tmp_path):
    (tmp_path / "a.jpg").write_text("image")
    result, plans, units, moved = _run(tmp_path, _row())
    assert result.status == "completed"
    assert moved == [tmp_path / "_Review/a.jpg"]
    assert plans[-1]["execution"]["culling_metadata_written"] is True
    assert units[-1]["next_image_index"] == 1


def test_resumes_after_move_without_moving_twice(tmp_path):
    target = tmp_path / "_Review/a.jpg"; target.parent.mkdir(); target.write_text("image")
    result, plans, units, moved = _run(tmp_path, _row({"target_path": "_Review/a.jpg", "moved": True}))
    assert result.status == "completed"
    assert moved == []
    assert plans[0]["execution"]["family_metadata_written"] is True


def test_does_not_advance_after_culling_failure(tmp_path):
    (tmp_path / "a.jpg").write_text("image")
    result, plans, units, _ = _run(tmp_path, _row(), (False, "exiftool_missing"))
    assert result.message == "culling_metadata:exiftool_missing"
    assert plans[-1]["execution"]["family_metadata_written"] is True
    assert units == []
