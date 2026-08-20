"""
Skript: app/execution_plan.py
Zweck: Plant deterministisch neue Batches und interne WorkUnits ohne Dateioperationen.
Autor: MaiTaiMa
Erstellt: 2026-08-17
Version: 1.1.0
Requires: Python 3.11

Änderungsprotokoll:
  2026-08-20 | 1.1.0 | B1: Laufzeitlimits für Run und Batch validiert.
  2026-08-17 | 1.0.0 | V12-03: Batch-Reihenfolge und Mengenlimit-Planung ergänzt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


class ExecutionPlanError(ValueError):
    """Beschreibt eine ungültige Planungs- oder Limitkonfiguration."""


@dataclass(frozen=True)
class ExecutionLimits:
    """Enthält die validierten Limits für einen lokalen Workflow-Run."""

    batch_order: str
    max_batches_per_run: int | None
    max_images_per_run: int | None
    max_images_per_batch: int | None
    max_runtime_seconds_per_run: int | None
    max_runtime_seconds_per_batch: int | None


@dataclass(frozen=True)
class BatchCandidate:
    """Beschreibt einen vollständig planbaren neuen Batch ohne Laufzeitmutationen."""

    batch_id: str
    path: Path
    image_names: tuple[str, ...]
    ordering_key: str
    ordering_source: str

    @property
    def image_count(self) -> int:
        """Liefert die deterministisch ermittelte Anzahl planbarer JPGs."""
        return len(self.image_names)


@dataclass(frozen=True)
class WorkUnitPlan:
    """Beschreibt eine noch nicht ausgeführte, interne Bildportion eines Batches."""

    workunit_id: str
    batch_id: str
    sequence: int
    image_names: tuple[str, ...]
    state: str = "pending"


@dataclass(frozen=True)
class RunPlan:
    """Beschreibt die vollständig ausgewählten Batches und geplanten WorkUnits eines Runs."""

    batch_order: str
    selected_batches: tuple[BatchCandidate, ...]
    workunits: tuple[WorkUnitPlan, ...]
    skipped_batches: tuple[dict[str, str], ...]

    @property
    def planned_batch_count(self) -> int:
        """Liefert die Anzahl vollständig ausgewählter neuer Batches."""
        return len(self.selected_batches)

    @property
    def planned_image_count(self) -> int:
        """Liefert die Bildsumme aller vollständig ausgewählten neuen Batches."""
        return sum(batch.image_count for batch in self.selected_batches)


_DATE_PREFIX = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})(?:_|$)")
_DATE_COMPACT = re.compile(r"^(?P<date>\d{8})(?:_|$)")


def _positive_int_or_none(value: Any, field_name: str) -> int | None:
    """Validiert null oder eine positive Ganzzahl und lehnt bool sowie nullnahe Werte ab."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ExecutionPlanError(f"workflow.{field_name} must be null or a positive integer")
    if value <= 0:
        raise ExecutionPlanError(f"workflow.{field_name} must be greater than zero")
    return value


def validate_execution_limits(workflow_cfg: Mapping[str, Any]) -> ExecutionLimits:
    """Validiert die V12-03-Konfiguration und liefert kanonische Limitwerte zurück."""
    if not isinstance(workflow_cfg, Mapping):
        raise ExecutionPlanError("workflow must be a mapping")

    batch_order = workflow_cfg.get("batch_order", "oldest_first")
    if batch_order not in {"oldest_first", "newest_first"}:
        raise ExecutionPlanError(
            "workflow.batch_order must be oldest_first or newest_first"
        )

    return ExecutionLimits(
        batch_order=batch_order,
        max_batches_per_run=_positive_int_or_none(
            workflow_cfg.get("max_batches_per_run"),
            "max_batches_per_run",
        ),
        max_images_per_run=_positive_int_or_none(
            workflow_cfg.get("max_images_per_run"),
            "max_images_per_run",
        ),
        max_images_per_batch=_positive_int_or_none(
            workflow_cfg.get("max_images_per_batch"),
            "max_images_per_batch",
        ),
        max_runtime_seconds_per_run=_positive_int_or_none(
            workflow_cfg.get("max_runtime_seconds_per_run"),
            "max_runtime_seconds_per_run",
        ),
        max_runtime_seconds_per_batch=_positive_int_or_none(
            workflow_cfg.get("max_runtime_seconds_per_batch"),
            "max_runtime_seconds_per_batch",
        ),
    )


def derive_ordering_key(batch_name: str) -> tuple[str, str]:
    """Ermittelt ein stabiles Sortierdatum oder verwendet den Namen als transparenten Fallback."""
    date_match = _DATE_PREFIX.match(batch_name)
    if date_match:
        return date_match.group("date").replace("-", ""), "normalized_date"

    compact_match = _DATE_COMPACT.match(batch_name)
    if compact_match:
        return compact_match.group("date"), "compact_date"

    return batch_name.casefold(), "name_fallback"


def make_batch_candidate(path: Path, image_names: Iterable[str]) -> BatchCandidate:
    """Erzeugt einen Kandidaten mit sortierter, unveränderlicher JPG-Namensliste."""
    ordering_key, ordering_source = derive_ordering_key(path.name)
    return BatchCandidate(
        batch_id=path.name,
        path=path,
        image_names=tuple(sorted(image_names, key=str.casefold)),
        ordering_key=ordering_key,
        ordering_source=ordering_source,
    )


def sort_new_batches(
    batches: Iterable[BatchCandidate],
    batch_order: str,
) -> list[BatchCandidate]:
    """Sortiert neue Batches deterministisch nach Datum, Name und relativem Pfad."""
    if batch_order not in {"oldest_first", "newest_first"}:
        raise ExecutionPlanError("unsupported batch order")

    ordered = sorted(
        batches,
        key=lambda batch: (
            batch.ordering_key,
            batch.batch_id.casefold(),
            str(batch.path).casefold(),
        ),
    )
    if batch_order == "newest_first":
        ordered.reverse()
    return ordered


def split_into_workunits(
    batch: BatchCandidate,
    max_images_per_batch: int | None,
) -> list[WorkUnitPlan]:
    """Teilt einen Batch rein planerisch in deterministische, noch nicht ausgeführte WorkUnits."""
    size = max_images_per_batch or max(1, batch.image_count)
    return [
        WorkUnitPlan(
            workunit_id=f"{batch.batch_id}:wu-{index:04d}",
            batch_id=batch.batch_id,
            sequence=index,
            image_names=batch.image_names[offset:offset + size],
        )
        for index, offset in enumerate(range(0, batch.image_count, size), start=1)
    ]


def build_run_plan(
    batches: Iterable[BatchCandidate],
    limits: ExecutionLimits,
) -> RunPlan:
    """Wählt ausschließlich vollständige neue Batches innerhalb der konfigurierten Limits aus."""
    selected: list[BatchCandidate] = []
    skipped: list[dict[str, str]] = []
    planned_images = 0

    for batch in sort_new_batches(batches, limits.batch_order):
        if batch.image_count == 0:
            skipped.append({"batch_id": batch.batch_id, "reason": "no_active_jpgs"})
            continue

        if (
            limits.max_batches_per_run is not None
            and len(selected) >= limits.max_batches_per_run
        ):
            skipped.append({"batch_id": batch.batch_id, "reason": "max_batches_per_run"})
            continue

        if (
            limits.max_images_per_run is not None
            and planned_images + batch.image_count > limits.max_images_per_run
        ):
            skipped.append({"batch_id": batch.batch_id, "reason": "max_images_per_run"})
            continue

        selected.append(batch)
        planned_images += batch.image_count

    workunits = tuple(
        unit
        for batch in selected
        for unit in split_into_workunits(batch, limits.max_images_per_batch)
    )

    return RunPlan(
        batch_order=limits.batch_order,
        selected_batches=tuple(selected),
        workunits=workunits,
        skipped_batches=tuple(skipped),
    )