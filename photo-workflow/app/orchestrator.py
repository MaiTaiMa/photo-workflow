from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .batch_layout import assert_review_state_valid, ensure_layout
from .batch_identity import batch_id
from .config_schema import config_fingerprint, effective_base_dir
from .phase1_state import assert_phase1_completed, transition
from .path_security import ensure_within, validate_publish_target
from .state_store import StateStore


class WorkflowGateError(RuntimeError):
    """Raised when a phase precondition is not fulfilled."""


@dataclass(frozen=True)
class PhaseContext:
    batch_id: str
    batch_path: Path
    config_fingerprint: str
    producer_version: str


class WorkflowOrchestrator:
    """Controlled integration boundary for the legacy workflow modules."""

    def __init__(self, config: dict[str, Any], *, runtime_root: str | Path,
                 producer_version: str = "ap21.1"):
        self.config = config
        self.store = StateStore(runtime_root)
        self.producer_version = producer_version

    def context(self, batch_path: str | Path) -> PhaseContext:
        root = effective_base_dir(self.config)
        path = ensure_within(root, batch_path, allow_missing=False)
        return PhaseContext(batch_id(batch_path), path,
                            config_fingerprint(self.config), self.producer_version)

    def start_phase1(self, batch_path: str | Path) -> PhaseContext:
        context = self.context(batch_path)
        ensure_layout(context.batch_path)
        transition(self.store, context.batch_id, "phase1_started",
                   producer_version=context.producer_version,
                   config_fingerprint=context.config_fingerprint,
                   source_batch_path=str(context.batch_path))
        return context

    def mark_phase1_moving(self, context: PhaseContext) -> None:
        transition(self.store, context.batch_id, "phase1_moving",
                   producer_version=context.producer_version,
                   config_fingerprint=context.config_fingerprint)

    def complete_phase1(self, context: PhaseContext, *, manifest_hash: str) -> None:
        assert_review_state_valid(context.batch_path)
        if not manifest_hash:
            raise WorkflowGateError("phase1_completed requires manifest_hash")
        transition(self.store, context.batch_id, "phase1_completed",
                   producer_version=context.producer_version,
                   config_fingerprint=context.config_fingerprint,
                   manifest_hash=manifest_hash)

    def gate_phase2(self, context: PhaseContext) -> None:
        assert_phase1_completed(self.store, context.batch_id)
        assert_review_state_valid(context.batch_path)

    def gate_phase3(self, context: PhaseContext, target: str | Path | None) -> None:
        self.gate_phase2(context)
        if target is not None:
            validate_publish_target(self.config, target)
