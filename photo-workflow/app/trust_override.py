# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/trust_override.py
# PURPOSE:     Persistiert den projektweiten manuellen Vertrauenswiderruf atomar.
# AUTHOR:      Matzethias
# DATE:        2026-08-26
# VERSION:     1.1.0
# REQUIRES:    Python 3.11, hashlib, json, pathlib
# CHANGES:
#   2026-08-26 | 1.1.0 | Widerruf, manueller Restore und Zustandszeitpunkte ergänzt.
# =============================================================================


from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "1.1"


# -----------------------------------------------------------------------------
# Fehler- und Hash-Hilfsfunktionen für den unveränderlichen Audit-State.
# -----------------------------------------------------------------------------
class TrustOverrideError(ValueError):
    """Beschreibt einen ungültigen oder beschädigten Override-State."""


def _utc_now() -> str:
    """Liefert einen UTC-Zeitstempel im kanonischen ISO-8601-Format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _digest(payload: dict[str, Any]) -> str:
    """Berechnet SHA-256 über den Payload ohne eigenes Hash-Feld."""
    unsigned = dict(payload)
    unsigned.pop("hash", None)
    text = json.dumps(
        unsigned,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# -----------------------------------------------------------------------------
# Store für genau einen projektweiten Override unterhalb des Runtime-Bereichs.
# Ein beschädigter vorhandener State wird nicht als inaktiv interpretiert.
# -----------------------------------------------------------------------------
class TrustOverrideStore:
    """Liest und schreibt den projektweiten Vertrauenswiderruf."""

    def __init__(self, runtime_path: str | Path, producer_version: str) -> None:
        """Initialisiert den Store unter dem kontrollierten Runtime-Pfad."""
        self.runtime_path = Path(runtime_path)
        self.producer_version = producer_version

    @property
    def path(self) -> Path:
        """Liefert den kanonischen Pfad des Override-Artefakts."""
        return self.runtime_path / "automation" / "trust_override.json"

    def load(self) -> dict[str, Any] | None:
        """Lädt und validiert den Override oder liefert None bei fehlender Datei."""
        target = self.path
        if not target.exists():
            return None

        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise TrustOverrideError(
                f"invalid trust override artifact: {target}"
            ) from exc

        self.validate(payload)
        return payload

    def validate(self, payload: dict[str, Any]) -> None:
        """Prüft Schema, Pflichtfelder und die Integrität des Payloads."""
        required = {
            "schema_version",
            "active",
            "reason",
            "set_at",
            "cleared_at",
            "producer_version",
            "hash",
            "auto_restore",
            "min_new_confirmed_batches_since_override",
            "confirmed_batches_since_override",
            "override_set_at",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise TrustOverrideError("invalid trust override schema")

        if payload["schema_version"] != SCHEMA_VERSION:
            raise TrustOverrideError("unsupported trust override schema")

        if not isinstance(payload["active"], bool):
            raise TrustOverrideError("active must be boolean")

        if not isinstance(payload["reason"], str) or not payload["reason"].strip():
            raise TrustOverrideError("reason must be non-empty")

        if not isinstance(payload["set_at"], str) or not payload["set_at"]:
            raise TrustOverrideError("set_at must be non-empty")

        if payload["cleared_at"] is not None and not isinstance(
            payload["cleared_at"],
            str,
        ):
            raise TrustOverrideError("cleared_at must be string or null")

        if payload["producer_version"] != self.producer_version:
            raise TrustOverrideError("producer version mismatch")

        if not isinstance(payload["auto_restore"], bool):
            raise TrustOverrideError("auto_restore must be boolean")

        if not isinstance(payload["min_new_confirmed_batches_since_override"], int):
            raise TrustOverrideError("min_new_confirmed_batches_since_override must be integer")

        if not isinstance(payload["confirmed_batches_since_override"], int):
            raise TrustOverrideError("confirmed_batches_since_override must be integer")

        if payload["override_set_at"] is not None and not isinstance(payload["override_set_at"], str):
            raise TrustOverrideError("override_set_at must be string or null")

        if not isinstance(payload["hash"], str) or payload["hash"] != _digest(payload):
            raise TrustOverrideError("trust override hash mismatch")

    def is_active(self) -> bool:
        """Liefert True nur bei vorhandenem und gültigem aktivem Override."""
        payload = self.load()
        return payload is not None and payload["active"] is True

    def write(
        self,
        reason: str,
        auto_restore: bool = False,
        min_new_confirmed_batches: int = 3,
        confirmed_batches: int = 0,
        override_set_at: str | None = None,
    ) -> dict[str, Any]:
        """Schreibt einen aktivierten Override atomar und gibt ihn zurück."""
        if not isinstance(reason, str) or not reason.strip():
            raise TrustOverrideError("reason must be non-empty")

        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "active": True,
            "reason": reason.strip(),
            "set_at": _utc_now(),
            "cleared_at": None,
            "producer_version": self.producer_version,
            "auto_restore": auto_restore,
            "min_new_confirmed_batches_since_override": min_new_confirmed_batches,
            "confirmed_batches_since_override": confirmed_batches,
            "override_set_at": override_set_at,
        }
        payload["hash"] = _digest(payload)

        target = self.path
        target.parent.mkdir(parents=True, exist_ok=True)

        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                json.dump(
                    payload,
                    handle,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        except Exception:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            raise

        return payload

    def restore(self) -> dict[str, Any]:
        """Deaktiviert den Override atomar und protokolliert den Restore."""
        payload = self.load()
        if payload is None:
            raise TrustOverrideError("trust override does not exist")

        restored = dict(payload)
        restored["active"] = False
        restored["cleared_at"] = _utc_now()
        restored["hash"] = _digest(restored)

        target = self.path
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                json.dump(
                    restored,
                    handle,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        except Exception:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            raise

        return restored

    def increment_confirmed_batches(self, config: Mapping[str, Any]) -> bool:
        """Inkrementiert den Zähler für neue bestätigte Batches seit dem Override.

        Returns True, wenn der Override dadurch automatisch gelöscht wurde.
        """
        data = self.load()
        if data is None or not data.get("active", False):
            return False

        auto_restore = bool(data.get("auto_restore", False))
        if not auto_restore:
            return False

        min_batches = int(data.get("min_new_confirmed_batches_since_override", 3))
        confirmed = int(data.get("confirmed_batches_since_override", 0)) + 1
        override_set_at = data.get("override_set_at")

        # Neuen Stand schreiben
        self.write(
            reason=data.get("reason", ""),
            auto_restore=auto_restore,
            min_new_confirmed_batches=min_batches,
            confirmed_batches=confirmed,
            override_set_at=override_set_at,
        )

        # Automatisch löschen, wenn Mindestanzahl erreicht
        if confirmed >= min_batches:
            self.restore()
            return True
        return False


def create_store(runtime_path: str | Path, producer_version: str) -> TrustOverrideStore:
    """Erzeugt einen Trust-Override-Store mit konsistenten Parametern."""
    return TrustOverrideStore(
        runtime_path=runtime_path,
        producer_version=producer_version,
    )


__all__ = [
    "SCHEMA_VERSION",
    "TrustOverrideError",
    "TrustOverrideStore",
    "create_store",
]