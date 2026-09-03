# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/trust_manager.py
# PURPOSE:     Batchbezogenes Trust-Level-System fuer KI-Automatik (TODO_v1.3
#              Modul 3). Ergaenzt den projektweiten trust_override.py um eine
#              feingranulare, batchweise Vertrauensbewertung.
# AUTHOR:      Matzethias
# DATE:        2026-08-31
# VERSION:     1.0.0
# REQUIRES:    Python 3.11, hashlib, json, pathlib
# CHANGES:
#   2026-08-31 | 1.0.0 | Initial: TrustManager gemaess TODO_v1.3.md Modul 3.
# =============================================================================

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional


SCHEMA_VERSION = "1.0"


class TrustLevel(Enum):
    """Drei Vertrauensstufen. Default ist immer LOW (nicht vertrauen)."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TrustManagerError(ValueError):
    """Beschreibt einen ungueltigen oder beschaedigten Trust-State."""


def _utc_now() -> str:
    """Liefert einen UTC-Zeitstempel im kanonischen ISO-8601-Format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _digest(payload: dict[str, Any]) -> str:
    """Berechnet SHA-256 ueber den Payload ohne eigenes Hash-Feld."""
    unsigned = dict(payload)
    unsigned.pop("hash", None)
    text = json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TrustManager:
    """Verwaltet batchbezogenen Trust-State fuer KI-Automatik."""

    def __init__(self, config: dict[str, Any], state_dir: Path) -> None:
        """
        Initialisiere den TrustManager.

        Args:
            config: Config-Dict (aus config.yaml geladen).
            state_dir: Pfad zum State-Verzeichnis (z.B. WORKFLOW_DATA/runtime/automation).
        """
        self.config = config
        self.state_file = state_dir / "trust_state.json"
        self.state = self._load_state()

    def _load_state(self) -> dict[str, Any]:
        """Lade Trust-State aus persistenter Datei."""
        if self.state_file.exists():
            try:
                loaded = json.loads(self.state_file.read_text(encoding="utf-8"))
                # B9: Validiere State fail-closed
                if loaded.get("hash") != _digest(loaded):
                    # Beschadigter State → neu starten
                    return self._empty_state()
                return loaded
            except (OSError, json.JSONDecodeError):
                # Beschadigter State → neu starten
                return self._empty_state()
        return self._empty_state()

    def _empty_state(self) -> dict[str, Any]:
        """Liefert leeren Initial-State."""
        return {
            "schema_version": SCHEMA_VERSION,
            "batches": {},
            "global_settings": {
                "min_validations_for_auto": 5,
                "discrepancy_reset_trust": True,
                "max_auto_approvals_before_revalidation": 10,
            },
        }

    def _save_state(self) -> None:
        """Speichere Trust-State atomar mit Hash-Integritaet."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(self.state)
        payload["hash"] = _digest(payload)

        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=self.state_file.parent, prefix=".trust_state_", suffix=".tmp"
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
            os.replace(tmp_path, self.state_file)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def _validate_state(self) -> None:
        """Pruefe Integritaet des geladenen States."""
        if "hash" not in self.state:
            raise TrustManagerError("missing hash in trust state")
        expected = _digest(self.state)
        if self.state["hash"] != expected:
            raise TrustManagerError("trust state hash mismatch")

    def get_trust_level(self, batch_id: str) -> TrustLevel:
        """
        Ermittle Trust-Level fuer einen Batch.

        Default ist immer LOW (nicht vertrauen).
        """
        batch = self.state["batches"].get(batch_id, {})
        validated = batch.get("validated_count", 0)
        discrepancies = batch.get("discrepancy_count", 0)

        if discrepancies > 0 and self.config.get("discrepancy_reset_trust", True):
            return TrustLevel.LOW

        min_for_auto = self.config.get("min_validations_for_auto", 5)
        if validated >= min_for_auto:
            return TrustLevel.HIGH
        elif validated >= 2:
            return TrustLevel.MEDIUM
        return TrustLevel.LOW

    def should_auto_approve(self, batch_id: str) -> bool:
        """
        Entscheide, ob ein Batch automatisch freigegeben wird.

        Nur bei HIGH-Level und nicht ueberschrittener Revalidierungsgrenze.
        """
        if not self.config.get("enabled", False):
            return False

        trust_level = self.get_trust_level(batch_id)
        if trust_level != TrustLevel.HIGH:
            return False

        batch = self.state["batches"].get(batch_id, {})
        auto_approvals = batch.get("auto_approvals", 0)
        max_auto = self.config.get("max_auto_approvals_before_revalidation", 10)
        if auto_approvals >= max_auto:
            return False

        return True

    def record_validation(
        self, batch_id: str, discrepancies: int = 0
    ) -> None:
        """
        Registriere manuelle Validierung fuer einen Batch.

        Args:
            batch_id: Batch-Identifier.
            discrepancies: Anzahl Diskrepanzen (KI vs. Mensch).
        """
        if batch_id not in self.state["batches"]:
            self.state["batches"][batch_id] = {
                "validated_count": 0,
                "discrepancy_count": 0,
                "auto_approvals": 0,
                "last_validated": None,
                "trust_level": "low",
            }

        batch = self.state["batches"][batch_id]
        batch["validated_count"] += 1
        batch["discrepancy_count"] += discrepancies
        batch["last_validated"] = _utc_now()
        batch["trust_level"] = self.get_trust_level(batch_id).value

        self._save_state()

    def record_auto_approval(self, batch_id: str) -> None:
        """Registriere automatisches Approval fuer einen Batch."""
        if batch_id not in self.state["batches"]:
            self.state["batches"][batch_id] = {
                "validated_count": 0,
                "discrepancy_count": 0,
                "auto_approvals": 0,
                "last_validated": None,
                "trust_level": "low",
            }

        self.state["batches"][batch_id]["auto_approvals"] += 1
        self._save_state()

    def reset_trust(self, batch_id: str) -> None:
        """Setze Trust fuer einen Batch zurueck auf LOW."""
        if batch_id in self.state["batches"]:
            self.state["batches"][batch_id] = {
                "validated_count": 0,
                "discrepancy_count": 0,
                "auto_approvals": 0,
                "last_validated": None,
                "trust_level": "low",
            }
            self._save_state()

    def get_status(self, batch_id: Optional[str] = None) -> dict[str, Any]:
        """
        Hole Trust-Status.

        Args:
            batch_id: Wenn None, gesamter State.
        """
        if batch_id:
            return self.state["batches"].get(batch_id, {})
        return self.state
