from pathlib import Path
from types import SimpleNamespace

from app import photo_workflow as workflow
from app.execution_plan import WorkUnitPlan
from app.phase1_analysis_plan import Phase1AnalysisPlanStore
from app.workunit_state import WorkUnitStateStore


def test_phase1_analyze_persists_plan_and_states_without_touching_images(
    tmp_path,
    monkeypatch,
):
    batch_id = "batch-1"
    batch_dir = tmp_path / batch_id
    batch_dir.mkdir()

    image_a = batch_dir / "a.jpg"
    image_b = batch_dir / "b.jpg"
    image_a.write_bytes(b"image-a")
    image_b.write_bytes(b"image-b")

    state_dir = tmp_path / "state"
    rows = [
        {
            "file": "a.jpg",
            "decision": "keep",
            "family_tags": [],
            "family_regions": [],
            "execution": {
                "target_relative_path": "_Keep/a.jpg",
                "moved": False,
                "family_metadata_written": False,
                "culling_metadata_written": False,
            },
        },
        {
            "file": "b.jpg",
            "decision": "review",
            "family_tags": [],
            "family_regions": [],
            "execution": {
                "target_relative_path": "_Review/b.jpg",
                "moved": False,
                "family_metadata_written": False,
                "culling_metadata_written": False,
            },
        },
    ]
    workunits = (
        WorkUnitPlan(
            workunit_id=f"{batch_id}:wu-0001",
            batch_id=batch_id,
            sequence=1,
            image_names=("a.jpg",),
        ),
        WorkUnitPlan(
            workunit_id=f"{batch_id}:wu-0002",
            batch_id=batch_id,
            sequence=2,
            image_names=("b.jpg",),
        ),
    )

    monkeypatch.setattr(workflow, "require_within", lambda *_: None)
    monkeypatch.setattr(
        workflow,
        "top_level_jpgs",
        lambda _: [image_a, image_b],
    )
    monkeypatch.setattr(
        workflow,
        "validate_execution_limits",
        lambda _: object(),
    )
    monkeypatch.setattr(
        workflow,
        "make_batch_candidate",
        lambda *_: object(),
    )
    monkeypatch.setattr(
        workflow,
        "build_run_plan",
        lambda *_: SimpleNamespace(workunits=workunits),
    )
    monkeypatch.setattr(
        workflow,
        "load_personal",
        lambda _: (None, {"model_version": "test-model"}),
    )
    monkeypatch.setattr(workflow, "load_family_model", lambda _: None)
    monkeypatch.setattr(workflow, "prepare_clip_context", lambda _: None)
    monkeypatch.setattr(
        workflow,
        "detect_manual_keep_images",
        lambda **_: ([], {"status": "none"}),
    )
    monkeypatch.setattr(
        workflow,
        "analyze_rows",
        lambda **_: SimpleNamespace(rows=rows),
    )
    monkeypatch.setattr(
        workflow,
        "build_persistable_analysis_rows",
        lambda analysis_rows, **_: analysis_rows,
    )
    monkeypatch.setattr(
        workflow,
        "get_runtime_paths",
        lambda _: (tmp_path / "runtime", state_dir, tmp_path / "logs"),
    )
    monkeypatch.setattr(
        workflow,
        "config_fingerprint",
        lambda _: "test-config-fingerprint",
    )
    monkeypatch.setattr(workflow, "log", lambda *_args, **_kwargs: None)

    cfg = {
        "workflow": {},
        "culling": {"move_files": True},
        "paths": {
            "manual_keep_inbox": str(tmp_path / "manual-keep-inbox"),
            "manual_keep_used": str(tmp_path / "manual-keep-used"),
        },
    }

    workflow.run_phase1_analyze(
        cfg,
        batch_id=batch_id,
        folder=str(batch_dir),
    )

    plans = Phase1AnalysisPlanStore(
        state_dir / "phase1_analysis_plans",
        workflow.SCRIPT_VERSION,
    )
    states = WorkUnitStateStore(
        state_dir / "phase1_workunits",
        workflow.SCRIPT_VERSION,
    )

    plan = plans.load(batch_id)

    assert plan is not None
    assert plan["batch_id"] == batch_id
    assert [row["file"] for row in plan["rows"]] == ["a.jpg", "b.jpg"]
    assert plan["rows"] == rows
    assert [unit["workunit_id"] for unit in plan["workunits"]] == [
        f"{batch_id}:wu-0001",
        f"{batch_id}:wu-0002",
    ]

    assert states.load(batch_id, f"{batch_id}:wu-0001")["state"] == "pending"
    assert states.load(batch_id, f"{batch_id}:wu-0002")["state"] == "pending"

    assert image_a.read_bytes() == b"image-a"
    assert image_b.read_bytes() == b"image-b"
    assert not (batch_dir / "_Keep").exists()
    assert not (batch_dir / "_Review").exists()

    workflow.run_phase1_analyze(
        cfg,
        batch_id=batch_id,
        folder=str(batch_dir),
    )

    assert plans.load(batch_id)["hash"] == plan["hash"]
    assert states.load(batch_id, f"{batch_id}:wu-0001")["state"] == "pending"
    assert states.load(batch_id, f"{batch_id}:wu-0002")["state"] == "pending"
    assert image_a.read_bytes() == b"image-a"
    assert image_b.read_bytes() == b"image-b"