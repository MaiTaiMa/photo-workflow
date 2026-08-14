"""
Skript: app/workflow_locks.py
Zweck: Verwaltet atomare, besitzgebundene Run- und Batch-Locks.
Autor: MaiTaiMa
Erstellt: 2026-08-14
Version: 1.0.0
Requires: Python 3.11

Änderungsprotokoll:
  2026-08-14 | 1.0.0 | V12-02: Allgemeine Workflow-Locks ergänzt.
"""

from __future__ import annotations

import json
import os
import secrets
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


class WorkflowLockError(RuntimeError):
    """Beschreibt einen nicht sicher erwerbbaren oder freigebbaren Workflow-Lock."""


@dataclass(frozen=True)
class WorkflowLock:
    """Beschreibt einen ausschließlich vom Besitzer freigebbaren Lock."""

    path: Path
    scope: str
    resource_id: str
    owner_token: str
    acquired_at: str


def _utc_now() -> str:
    """Liefert einen UTC-Zeitstempel im ISO-8601-Format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_resource_id(value: str) -> str:
    """Blockiert Pfadtraversal und unzulässige Bezeichner in Lock-Dateinamen."""
    if not value or Path(value).name != value or value in {".", ".."}:
        raise WorkflowLockError("unsafe lock resource identifier")
    return value


class WorkflowLockManager:
    """Erwirbt globale Run-Locks und batchspezifische Locks atomar."""

    def __init__(self, lock_dir: str | Path) -> None:
        """Initialisiert das kontrollierte Lock-Verzeichnis."""
        self.lock_dir = Path(lock_dir)

    def _path_for(self, scope: str, resource_id: str) -> Path:
        """Erzeugt einen sicheren Lock-Pfad für Scope und Ressource."""
        _validate_resource_id(scope)
        _validate_resource_id(resource_id)
        return self.lock_dir / f"{scope}__{resource_id}.lock"

    def acquire(self, scope: str, resource_id: str) -> WorkflowLock:
        """Erwirbt einen Lock mit exklusiver Dateierzeugung oder bricht fail-closed ab."""
        path = self._path_for(scope, resource_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        owner_token = secrets.token_urlsafe(24)
        acquired_at = _utc_now()
        payload = {
            "schema_version": "1.0",
            "scope": scope,
            "resource_id": resource_id,
            "owner_token": owner_token,
            "acquired_at": acquired_at,
            "pid": os.getpid(),
        }
        try:
            descriptor = os.open(
                path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError as exc:
            raise WorkflowLockError(f"lock already held: {path}") from exc

        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            path.unlink(missing_ok=True)
            raise

        return WorkflowLock(path, scope, resource_id, owner_token, acquired_at)

    def acquire_run_lock(self) -> WorkflowLock:
        """Erwirbt den globalen Lock für genau einen produktiven Workflow-Lauf."""
        return self.acquire("run", "global")

    def acquire_batch_lock(self, batch_id: str) -> WorkflowLock:
        """Erwirbt den Lock für genau einen Batch innerhalb eines Workflow-Laufs."""
        return self.acquire("batch", _validate_resource_id(batch_id))

    def release(self, lock: WorkflowLock) -> None:
        """Gibt ausschließlich einen Lock des nachgewiesenen Besitzers frei."""
        try:
            payload = json.loads(lock.path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise WorkflowLockError(f"lock missing: {lock.path}") from exc
        except json.JSONDecodeError as exc:
            raise WorkflowLockError(f"lock is invalid: {lock.path}") from exc

        if payload.get("owner_token") != lock.owner_token:
            raise WorkflowLockError("lock owner token mismatch")
        if payload.get("scope") != lock.scope:
            raise WorkflowLockError("lock scope mismatch")
        if payload.get("resource_id") != lock.resource_id:
            raise WorkflowLockError("lock resource mismatch")
        lock.path.unlink()

    @contextmanager
    def run_lock(self) -> Iterator[WorkflowLock]:
        """Hält den globalen Run-Lock bis zum kontrollierten Verlassen des Kontexts."""
        lock = self.acquire_run_lock()
        try:
            yield lock
        finally:
            self.release(lock)

    @contextmanager
    def batch_lock(self, batch_id: str) -> Iterator[WorkflowLock]:
        """Hält einen Batch-Lock bis zum kontrollierten Verlassen des Kontexts."""
        lock = self.acquire_batch_lock(batch_id)
        try:
            yield lock
        finally:
            self.release(lock)