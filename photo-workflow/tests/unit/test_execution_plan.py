# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_execution_plan.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


from pathlib import Path

import pytest

from app.execution_plan import (
    ExecutionPlanError,
    build_run_plan,
    make_batch_candidate,
    validate_execution_limits,
)


def candidate(name: str, count: int):
    return make_batch_candidate(
        Path('/tmp') / name,
        [f'IMG_{index:04d}.JPG' for index in range(count)],
    )


def test_oldest_first_uses_normalized_date_then_name() -> None:
    limits = validate_execution_limits({'batch_order': 'oldest_first'})
    plan = build_run_plan(
        [
            candidate('2024-08-03_B.JPG', 1),
            candidate('2024-08-01_Z.JPG', 1),
            candidate('2024-08-01_A.JPG', 1),
        ],
        limits,
    )

    assert [batch.batch_id for batch in plan.selected_batches] == [
        '2024-08-01_A.JPG',
        '2024-08-01_Z.JPG',
        '2024-08-03_B.JPG',
    ]


def test_newest_first_reverses_deterministic_order() -> None:
    limits = validate_execution_limits({'batch_order': 'newest_first'})
    plan = build_run_plan(
        [candidate('2024-08-01_A', 1), candidate('2024-08-03_B', 1)],
        limits,
    )

    assert [batch.batch_id for batch in plan.selected_batches] == [
        '2024-08-03_B',
        '2024-08-01_A',
    ]


def test_max_batches_selects_only_complete_batches() -> None:
    limits = validate_execution_limits({'max_batches_per_run': 1})
    plan = build_run_plan(
        [candidate('2024-08-01_A', 2), candidate('2024-08-02_B', 2)],
        limits,
    )

    assert plan.planned_batch_count == 1
    assert plan.planned_image_count == 2
    assert plan.skipped_batches == (
        {'batch_id': '2024-08-02_B', 'reason': 'max_batches_per_run'},
    )


def test_max_images_never_selects_a_partial_batch() -> None:
    limits = validate_execution_limits({'max_images_per_run': 3})
    plan = build_run_plan(
        [candidate('2024-08-01_A', 2), candidate('2024-08-02_B', 2)],
        limits,
    )

    assert [batch.batch_id for batch in plan.selected_batches] == ['2024-08-01_A']
    assert plan.planned_image_count == 2
    assert plan.skipped_batches == (
        {'batch_id': '2024-08-02_B', 'reason': 'max_images_per_run'},
    )


def test_max_images_per_batch_creates_pending_workunits() -> None:
    limits = validate_execution_limits({'max_images_per_batch': 2})
    plan = build_run_plan([candidate('2024-08-01_A', 5)], limits)

    assert [len(unit.image_names) for unit in plan.workunits] == [2, 2, 1]
    assert [unit.state for unit in plan.workunits] == ['pending', 'pending', 'pending']


@pytest.mark.parametrize(
    'workflow_cfg',
    [
        {'batch_order': 'random'},
        {'max_batches_per_run': 0},
        {'max_images_per_run': True},
        {'max_images_per_batch': '10'},
    ],
)
def test_invalid_execution_config_is_rejected(workflow_cfg: dict) -> None:
    with pytest.raises(ExecutionPlanError):
        validate_execution_limits(workflow_cfg)

def test_runtime_limits_accept_positive_values_and_none() -> None:
    limits = validate_execution_limits(
        {
            "max_runtime_seconds_per_run": 600,
            "max_runtime_seconds_per_batch": None,
        }
    )

    assert limits.max_runtime_seconds_per_run == 600
    assert limits.max_runtime_seconds_per_batch is None


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("max_runtime_seconds_per_run", 0),
        ("max_runtime_seconds_per_run", -1),
        ("max_runtime_seconds_per_run", True),
        ("max_runtime_seconds_per_run", 1.5),
        ("max_runtime_seconds_per_run", "60"),
        ("max_runtime_seconds_per_batch", 0),
        ("max_runtime_seconds_per_batch", -1),
        ("max_runtime_seconds_per_batch", True),
        ("max_runtime_seconds_per_batch", 1.5),
        ("max_runtime_seconds_per_batch", "60"),
    ),
)
def test_invalid_runtime_limits_are_rejected(field: str, value: object) -> None:
    with pytest.raises(ExecutionPlanError):
        validate_execution_limits({field: value})