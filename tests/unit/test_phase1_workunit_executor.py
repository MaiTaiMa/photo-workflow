from app.phase1_workunit_executor import execute_next_image


def _row(target="_Review/a.jpg", execution=None):
    return {
        "file": "a.jpg",
        "_family_tags": ["family:test"],
        "_family_regions": [],
        "execution": execution or {"target_path": target},
    }


def _run(tmp_path, row, workunit=None, family=(True, "ok"), culling=(True, "written")):
    plan_updates, unit_updates = [], []
    moved = []
    workunit = workunit or {"state": "pending", "next_image_index": 0, "images": ["a.jpg"]}

    def move(source, target):
        source.rename(target)
        moved.append((source, target))

    result = execute_next_image(
        root=tmp_path,
        workunit=workunit,
        plan_rows=[row],
        cfg={},
        update_plan=plan_updates.append,
        update_workunit=unit_updates.append,
        move_file=move,
        write_family=lambda *_: family,
        write_culling=lambda *_: culling,
    )
    return result, plan_updates, unit_updates, moved


def test_executes_one_image_and_completes_workunit(tmp_path):
    (tmp_path / "a.jpg").write_text("image")
    result, plans, units, moved = _run(tmp_path, _row())

    assert result.status == "completed"
    assert len(moved) == 1
    assert (tmp_path / "_Review/a.jpg").exists()
    assert plans[-1]["execution"]["culling_metadata_written"] is True
    assert units[-1] == {"state": "completed", "next_image_index": 1, "images": ["a.jpg"]}


def test_resumes_after_move_without_moving_twice(tmp_path):
    target = tmp_path / "_Review/a.jpg"
    target.parent.mkdir()
    target.write_text("image")
    row = _row(execution={"target_path": "_Review/a.jpg", "moved": True})

    result, plans, units, moved = _run(tmp_path, row)

    assert result.status == "completed"
    assert moved == []
    assert plans[0]["execution"]["family_metadata_written"] is True
    assert units[-1]["next_image_index"] == 1


def test_does_not_advance_after_culling_failure(tmp_path):
    (tmp_path / "a.jpg").write_text("image")
    result, plans, units, moved = _run(tmp_path, _row(), culling=(False, "exiftool_missing"))

    assert result.status == "failed"
    assert result.message == "culling_metadata:exiftool_missing"
    assert moved
    assert plans[-1]["execution"]["family_metadata_written"] is True
    assert units == []
