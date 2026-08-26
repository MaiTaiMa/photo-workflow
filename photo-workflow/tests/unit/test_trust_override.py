"""
Skript: tests/unit/test_trust_override.py
Zweck: Prüft Widerruf, Restore und Integrität des Trust-Override-Stores.
Autor: Matthias Streser
Datum: 2026-08-26
Version: 1.0.0
Requires: Python 3.11, pytest, app.trust_override

Änderungsprotokoll:
  2026-08-26 | 1.0.0 | Store-Tests für Widerruf und manuellen Restore ergänzt.
  2026-08-27 | 1.1.0 | Tests für increment_confirmed_batches() und auto_restore ergänzt.
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


def test_increment_confirmed_batches_no_override(tmp_path: Path) -> None:
    """Kein Override vorhanden -> increment_confirmed_batches() gibt False."""
    store = TrustOverrideStore(tmp_path, "1.0")
    config: dict = {}

    result = store.increment_confirmed_batches(config)

    assert result is False
    assert store.path.exists() is False


def test_increment_confirmed_batches_auto_restore_disabled(tmp_path: Path) -> None:
    """auto_restore=false -> Zähler wird nicht inkrementiert, gibt False."""
    store = TrustOverrideStore(tmp_path, "1.0")
    store.write(
        reason="test override",
        auto_restore=False,
        min_new_confirmed_batches=3,
        confirmed_batches=0,
        override_set_at=None,
    )
    config: dict = {}

    result = store.increment_confirmed_batches(config)

    assert result is False
    data = store.load()
    assert data["confirmed_batches_since_override"] == 0


def test_increment_confirmed_batches_increments_counter(tmp_path: Path) -> None:
    """auto_restore=true, aber Mindestanzahl noch nicht erreicht -> Zähler inkrementieren."""
    store = TrustOverrideStore(tmp_path, "1.0")
    store.write(
        reason="test override",
        auto_restore=True,
        min_new_confirmed_batches=3,
        confirmed_batches=0,
        override_set_at=None,
    )
    config: dict = {}

    result = store.increment_confirmed_batches(config)

    assert result is False
    data = store.load()
    assert data["confirmed_batches_since_override"] == 1
    assert data["active"] is True


def test_increment_confirmed_batches_auto_restore_after_threshold(tmp_path: Path) -> None:
    """auto_restore=true, Mindestanzahl erreicht -> Override wird gelöscht."""
    store = TrustOverrideStore(tmp_path, "1.0")
    store.write(
        reason="test override",
        auto_restore=True,
        min_new_confirmed_batches=2,
        confirmed_batches=1,
        override_set_at=None,
    )
    config: dict = {}

    result = store.increment_confirmed_batches(config)

    assert result is True
    data = store.load()
    assert data["active"] is False
    assert data["cleared_at"] is not None


def test_increment_confirmed_batches_respects_min_batches(tmp_path: Path) -> None:
    """Zähler muss genau min_new_confirmed_batches erreichen für auto_restore."""
    store = TrustOverrideStore(tmp_path, "1.0")
    store.write(
        reason="test override",
        auto_restore=True,
        min_new_confirmed_batches=5,
        confirmed_batches=0,
        override_set_at=None,
    )
    config: dict = {}

    # 4x inkrementieren -> noch nicht gelöscht
    for i in range(4):
        result = store.increment_confirmed_batches(config)
        assert result is False, f"Nach {i+1} Batches sollte noch nicht gelöscht sein"
        data = store.load()
        assert data["confirmed_batches_since_override"] == i + 1
        assert data["active"] is True

    # 5. Batch -> gelöscht
    result = store.increment_confirmed_batches(config)
    assert result is True
    data = store.load()
    assert data["active"] is False
