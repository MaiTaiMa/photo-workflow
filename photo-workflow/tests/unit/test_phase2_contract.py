"""
Skript: tests/unit/test_phase2_contract.py
Zweck: Testet Phase-2-Hardening (cleanup_review_rejected, move_to_temp_final).
Autor: MaiTaiMa
Erstellt: 2026-08-09
Version: 2.0 (angepasst an neue phase2_contract.py)

Änderungsprotokoll:
  2026-08-22 | C1.2.3 | Kanonische Review-/Rejected-Ordnernamen ohne Unterstrich vereinheitlicht.
  2026-08-09 | 1.0 | Initiale Version mit Phase2GateError
  2026-08-09 | 2.0 | Umstellung auf cleanup_review_rejected + move_to_temp_final
"""

import pytest
from pathlib import Path
import shutil
import tempfile
import yaml

from app.phase2_contract import (
    cleanup_review_rejected,
    move_to_temp_final,
    verify_cleanup_complete,
)


@pytest.fixture
def test_dirs():
    """Erstellt temporäre Test-Verzeichnisse."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        batch = tmpdir / "2025-11-01"
        review = batch / "Review"
        rejected = batch / "Rejected"
        temp_done = tmpdir / "03_TEMP_DONE"
        temp_error = tmpdir / "00_TEMP_ERROR"
        temp_final = tmpdir / "04_TEMP_FINAL"
        
        batch.mkdir()
        review.mkdir()
        rejected.mkdir()
        temp_done.mkdir()
        temp_error.mkdir()
        temp_final.mkdir()
        
        # Test-Bilder erstellen
        (review / "test_review.JPG").touch()
        (rejected / "test_rejected.JPG").touch()
        
        cfg = {
            'paths': {
                'temp_done': str(temp_done),
                'temp_error': str(temp_error),
                'temp_final': str(temp_final),
            },
            'phase2': {
                'cleanup_review_rejected': True,
                'move_to_temp_final': True,
                'dry_run': False,
            },
        }
        
        yield {
            'batch': batch,
            'review': review,
            'rejected': rejected,
            'temp_done': temp_done,
            'temp_error': temp_error,
            'temp_final': temp_final,
            'cfg': cfg,
        }


def test_cleanup_review_rejected(test_dirs):
    """Testet cleanup_review_rejected() mit Review und Rejected."""
    result = cleanup_review_rejected(
        batch_path=str(test_dirs['batch']),
        cfg=test_dirs['cfg'],
        dry_run=False,
    )
    
    assert result['status'] == 'ok'
    assert result['review_keep_moved'] + result['review_reject_moved'] >= 0
    assert result['rejected_moved'] >= 0
    
    # Ordner sollten gelöscht sein
    assert not test_dirs['review'].exists()
    assert not test_dirs['rejected'].exists()


def test_move_to_temp_final(test_dirs):
    """Testet move_to_temp_final() mit korrektem Pfad."""
    result = move_to_temp_final(
        batch_path=str(test_dirs['batch']),
        cfg=test_dirs['cfg'],
        dry_run=False,
    )
    
    assert result['success'] == True
    assert result['target_path'] == str(test_dirs['temp_final'] / test_dirs['batch'].name)
    assert result['error'] == ''


def test_verify_cleanup_complete(test_dirs):
    """Testet verify_cleanup_complete() mit leeren Ordnern."""
    # Ordner vorher bereinigen (shutil.rmtree für nicht-leere Ordner)
    shutil.rmtree(test_dirs['review'])
    shutil.rmtree(test_dirs['rejected'])
    
    result = verify_cleanup_complete(str(test_dirs['batch']))
    
    assert result['review_empty'] == True
    assert result['rejected_empty'] == True
    assert result['complete'] == True


def test_verify_cleanup_complete_with_files(test_dirs):
    """Testet verify_cleanup_complete() mit Dateien in Ordnern."""
    result = verify_cleanup_complete(str(test_dirs['batch']))
    
    assert result['review_empty'] == False
    assert result['rejected_empty'] == False
    assert result['complete'] == False
    assert len(result['review_remaining']) == 1
    assert len(result['rejected_remaining']) == 1