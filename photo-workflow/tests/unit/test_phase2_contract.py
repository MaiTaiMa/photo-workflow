# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_phase2_contract.py
# PURPOSE:     Testet Phase-2-Hardening (cleanup_review_rejected, move_to_temp_final).
# AUTHOR:      Matzethias
# DATE:        2026-08-09
# VERSION:     2.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   2026-08-22 | C1.2.3 | Kanonische Review-/Rejected-Ordnernamen ohne Unterstrich vereinheitlicht.
#   2026-08-09 | 1.0 | Initiale Version mit Phase2GateError
#   2026-08-09 | 2.0 | Umstellung auf cleanup_review_rejected + move_to_temp_final
# =============================================================================


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
    """Testet move_to_temp_final() mit korrektem Pfad (Move wenn Ziel nicht existiert)."""
    # temp_final Verzeichnis erstellen
    test_dirs['temp_final'].mkdir(parents=True, exist_ok=True)
    
    # cfg um alle benötigten paths erweitern
    cfg = test_dirs['cfg'].copy()
    cfg['paths'] = cfg.get('paths', {}).copy()
    cfg['paths']['temp_final'] = str(test_dirs['temp_final'])
    cfg['paths']['base_dir'] = str(test_dirs['batch'].parent)  # Parent von batch
    # Log-Dateien erstellen
    log_dir = test_dirs['batch'].parent / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    cfg['paths']['log_file'] = str(log_dir / 'workflow.log')
    cfg['paths']['error_log'] = str(log_dir / 'workflow_error.log')
    
    if 'phase2' not in cfg:
        cfg['phase2'] = {}
    cfg['phase2']['move_to_temp_final'] = True
    
    if 'safety' not in cfg:
        cfg['safety'] = {'require_paths_within_basedir': True}

    try:
        result = move_to_temp_final(
            batch_path=str(test_dirs['batch']),
            cfg=cfg,
            dry_run=False,
        )
        print(f'DEBUG: result={result}')
    except Exception as e:
        print(f'DEBUG: Exception={e}')
        import traceback
        traceback.print_exc()
        raise

    assert result['success'] == True
    assert result['target_path'] == str(test_dirs['temp_final'] / test_dirs['batch'].name)
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

def test_move_to_temp_final_date_prefix(test_dirs):
    """Testet move_to_temp_final() mit datum-basiertem Merge (Suffix-Priorität)."""
    # temp_final Verzeichnis erstellen
    test_dirs['temp_final'].mkdir(parents=True, exist_ok=True)
    
    # Existierenden Ordner mit Suffix erstellen (manuell benannt, hat Priorität)
    existing_batch = test_dirs['temp_final'] / '2025-11-01_Urlaub'
    existing_batch.mkdir()
    (existing_batch / 'existing.jpg').write_text('existing')
    
    # cfg um paths und merge_by_date_prefix erweitern
    cfg = test_dirs['cfg'].copy()
    cfg['paths'] = cfg.get('paths', {}).copy()
    cfg['paths']['temp_final'] = str(test_dirs['temp_final'])
    cfg['paths']['base_dir'] = str(test_dirs['batch'].parent)
    log_dir = test_dirs['batch'].parent / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    cfg['paths']['log_file'] = str(log_dir / 'workflow.log')
    cfg['paths']['error_log'] = str(log_dir / 'workflow_error.log')
    
    if 'phase2' not in cfg:
        cfg['phase2'] = {}
    cfg['phase2']['move_to_temp_final'] = True
    cfg['phase2']['merge_by_date_prefix'] = True  # Prefix-Match aktivieren
    
    if 'safety' not in cfg:
        cfg['safety'] = {'require_paths_within_basedir': True}
    
    # Batch ohne Suffix - soll in existierenden Ordner mit Suffix mergen
    batch_plain = test_dirs['batch'].parent / '2025-11-01'
    batch_plain.mkdir(exist_ok=True)
    (batch_plain / 'new.jpg').write_text('new')
    
    result = move_to_temp_final(
        batch_path=str(batch_plain),
        cfg=cfg,
        dry_run=False,
    )
    
    assert result['success'] == True
    # Sollte in existierenden Ordner mit Suffix gemerged sein (Suffix-Priorität!)
    assert result['target_path'] == str(existing_batch)
    assert (existing_batch / 'new.jpg').exists()
    assert (existing_batch / 'existing.jpg').exists()


def test_move_to_temp_final_date_prefix_reverse(test_dirs):
    """Testet move_to_temp_final() mit datum-basiertem Merge (Quelle mit Suffix)."""
    # temp_final Verzeichnis erstellen
    test_dirs['temp_final'].mkdir(parents=True, exist_ok=True)
    
    # Existierenden Ordner ohne Suffix erstellen
    existing_batch = test_dirs['temp_final'] / '2025-11-01'
    existing_batch.mkdir()
    (existing_batch / 'existing.jpg').write_text('existing')
    
    # cfg um paths und merge_by_date_prefix erweitern
    cfg = test_dirs['cfg'].copy()
    cfg['paths'] = cfg.get('paths', {}).copy()
    cfg['paths']['temp_final'] = str(test_dirs['temp_final'])
    cfg['paths']['base_dir'] = str(test_dirs['batch'].parent)
    log_dir = test_dirs['batch'].parent / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    cfg['paths']['log_file'] = str(log_dir / 'workflow.log')
    cfg['paths']['error_log'] = str(log_dir / 'workflow_error.log')
    
    if 'phase2' not in cfg:
        cfg['phase2'] = {}
    cfg['phase2']['move_to_temp_final'] = True
    cfg['phase2']['merge_by_date_prefix'] = True
    
    if 'safety' not in cfg:
        cfg['safety'] = {'require_paths_within_basedir': True}
    
    # Batch mit Suffix - soll in existierenden Ordner ohne Suffix mergen
    batch_with_suffix = test_dirs['batch'].parent / '2025-11-01_Urlaub'
    batch_with_suffix.mkdir(exist_ok=True)
    (batch_with_suffix / 'new.jpg').write_text('new')
    
    result = move_to_temp_final(
        batch_path=str(batch_with_suffix),
        cfg=cfg,
        dry_run=False,
    )
    
    assert result['success'] == True
    # Sollte in existierenden Ordner ohne Suffix gemerged sein
    assert result['target_path'] == str(existing_batch)
    assert (existing_batch / 'new.jpg').exists()
    assert (existing_batch / 'existing.jpg').exists()

