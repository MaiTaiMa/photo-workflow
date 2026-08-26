"""
Skript: tests/unit/test_trust_override.py
Zweck: Prüft Widerruf, Restore und Integrität des Trust-Override-Stores.
Autor: Matthias Streser
Datum: 2026-08-26
Version: 1.0.0
Requires: Python 3.11, pytest, app.trust_override

Änderungsprotokoll:
  2026-08-26 | 1.0.0 | Store-Tests für Widerruf und manuellen Restore ergänzt.
"""

from pathlib import Path

import pytest

from app.trust_override import TrustOverrideError, TrustOverrideStore


def test_write_creates_active_override(tmp_path: Path) -> None:
    store = TrustOverrideStore(tmp_path, "1.0")

    payload = store.write("manueller Widerruf")

    assert payload["active"] is True
    assert payload["reason"] == "manueller Widerruf"
    assert payload["set_at"]
    assert payload["cleared_at"] is None
    assert store.is_active() is True


def test_restore_clears_override_and_preserves_set_time(
    tmp_path: Path,
) -> None:
    store = TrustOverrideStore(tmp_path, "1.0")
    payload = store.write("manueller Widerruf")

    restored = store.restore()

    assert restored["active"] is False
    assert restored["set_at"] == payload["set_at"]
    assert restored["cleared_at"]
    assert store.is_active() is False
    assert store.load() == restored


def test_restore_requires_existing_override(tmp_path: Path) -> None:
    store = TrustOverrideStore(tmp_path, "1.0")

    with pytest.raises(TrustOverrideError, match="does not exist"):
        store.restore()


def test_invalid_override_is_rejected(tmp_path: Path) -> None:
    store = TrustOverrideStore(tmp_path, "1.0")
    target = store.path
    target.parent.mkdir(parents=True)
    target.write_text("{}", encoding="utf-8")

    with pytest.raises(TrustOverrideError):
        store.load()
