# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/integration/test_phase1_workunit_runtime_limits.py
# PURPOSE:     Prüft sichere Zeitlimit-Pausen vor Phase-1-Bildschritten.
# AUTHOR:      Matzethias
# DATE:        2026-08-20
# VERSION:     1.0.0
# REQUIRES:    Python 3.11, pytest
# CHANGES:
#   2026-08-22 | C1.2.3 | Kanonische Review-/Rejected-Ordnernamen ohne Unterstrich vereinheitlicht.
#   2026-08-20 | 1.0.0 | B2.1: Integrationstests für Run- und Batch-Zeitlimits ergänzt.
# =============================================================================


from pathlib import Path

import pytest

from app import photo_workflow as workflow
from app.pause_checkpoint import PauseCheckpointStore
from app.phase1_analysis_plan import Phase1AnalysisPlanStore
from app.phase1_runtime_budget_state import Phase1RuntimeBudgetStateStore
from app.runtime_budget import RuntimeBudget
from app.runtime_control import RuntimeControl
from app.workunit_state import WorkUnitStateStore


class ManualClock:
    """Liefert kontrollierbare monotone Zeit für Zeitlimit-Tests."""

    def __init__(self, value: float = 0.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def _cfg(base_dir: Path, *, run_limit, batch_limit) -> dict:
    return {
        "paths": {
            "base_dir": str(base_dir),
            "log_file": str(base_dir / "process.log"),
            "error_log": str(base_dir / "error.log"),
        },
        "safety": {"require_paths_within_base_dir": True},
        "workflow": {
            "max_runtime_seconds_per_run": run_limit,
            "max_runtime_seconds_per_batch": batch_limit,
        },
    }


def _initialize_batch(base_dir: Path, batch_id: str) -> tuple[Path, Path]:
    workdir = base_dir / batch_id
    workdir.mkdir()
    image = workdir / "a.jpg"
    image.write_bytes(b"image")

    state_dir = base_dir / "WORKFLOW_DATA" / "runtime" / "state"
    plans = Phase1AnalysisPlanStore(
        state_dir / "phase1_analysis_plans",
        workflow.SCRIPT_VERSION,
    )
    states = WorkUnitStateStore(
        state_dir / "phase1_workunits",
        workflow.SCRIPT_VERSION,
    )

    plans.write(
        batch_id=batch_id,
        rows=[
            {
                "file": "a.jpg",
                "family_tags": [],
                "family_regions": [],
                "execution": {
                    "target_relative_path": "Review/a.jpg",
                    "moved": False,
                    "family_metadata_written": False,
                    "culling_metadata_written": False,
                },
            }
        ],
        workunits=[
            {
                "workunit_id": f"{batch_id}:wu-0001",
                "image_names": ["a.jpg"],
            }
        ],
        config_fingerprint="test-config",
    )
    states.initialize(
        batch_id=batch_id,
        workunit_id=f"{batch_id}:wu-0001",
        image_names=("a.jpg",),
        config_fingerprint="test-config",
    )
    return workdir, state_dir


@pytest.mark.parametrize(
    ("run_limit", "batch_limit", "reason"),
    (
        (1, None, "max_runtime_seconds_per_run"),
        (None, 1, "max_runtime_seconds_per_batch"),
    ),
)
def test_expired_budget_pauses_before_image_operation(
    tmp_path,
    run_limit,
    batch_limit,
    reason,
) -> None:
    batch_id = "batch-a"
    workdir, state_dir = _initialize_batch(tmp_path, batch_id)
    clock = ManualClock(0.0)
    run_budget = RuntimeBudget(run_limit, clock=clock)

    if batch_limit is not None:
        budget_states = Phase1RuntimeBudgetStateStore(
            state_dir / "phase1_runtime_budgets",
            workflow.SCRIPT_VERSION,
        )
        budget_states.add_active_seconds(batch_id=batch_id, seconds=1.0)

    clock.value = 1.0
    cfg = _cfg(tmp_path, run_limit=run_limit, batch_limit=batch_limit)
    pause_store = PauseCheckpointStore(state_dir, workflow.SCRIPT_VERSION)
    runtime = RuntimeControl()

    workflow.run_phase1_workunit(
        cfg,
        batch_id=batch_id,
        folder=str(workdir),
        runtime=runtime,
        pause_store=pause_store,
        config_fingerprint_value="test-config",
        run_budget=run_budget,
        clock=clock,
    )

    states = WorkUnitStateStore(
        state_dir / "phase1_workunits",
        workflow.SCRIPT_VERSION,
    )
    plan = Phase1AnalysisPlanStore(
        state_dir / "phase1_analysis_plans",
        workflow.SCRIPT_VERSION,
    ).load(batch_id)
    pause = pause_store.load(batch_id)

    assert (workdir / "a.jpg").exists()
    assert not (workdir / "Review" / "a.jpg").exists()
    assert states.load(batch_id, f"{batch_id}:wu-0001")["state"] == "pending"
    assert plan["rows"][0]["execution"]["moved"] is False
    assert pause["pause_reason"] == reason
    assert pause["checkpoint"] == "before_phase1_workunit"
    assert pause["workunit_id"] == f"{batch_id}:wu-0001"


def test_completed_step_adds_active_time_to_batch_state(
    tmp_path,
    monkeypatch,
) -> None:
    batch_id = "batch-a"
    workdir, state_dir = _initialize_batch(tmp_path, batch_id)
    clock = ManualClock(0.0)

    class FakeRunner:
        def __init__(self, *_args) -> None:
            pass

        def run_next(self, **_kwargs):
            clock.value = 2.5
            return type(
                "Result",
                (),
                {"state": "in_progress", "image_index": 0, "message": ""},
            )()

    monkeypatch.setattr(workflow, "Phase1WorkUnitRunner", FakeRunner)

    cfg = _cfg(tmp_path, run_limit=None, batch_limit=None)
    workflow.run_phase1_workunit(
        cfg,
        batch_id=batch_id,
        folder=str(workdir),
        runtime=RuntimeControl(),
        pause_store=PauseCheckpointStore(
            state_dir,
            workflow.SCRIPT_VERSION,
        ),
        config_fingerprint_value="test-config",
        run_budget=RuntimeBudget(None, clock=clock),
        clock=clock,
    )

    budget_states = Phase1RuntimeBudgetStateStore(
        state_dir / "phase1_runtime_budgets",
        workflow.SCRIPT_VERSION,
    )
    record = budget_states.load(batch_id)

    assert record is not None
    assert record["active_seconds"] == 2.5