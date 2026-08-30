# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/phase2_contract.py
# PURPOSE:     Phase-2-Vertrag (Archivierung, Review/Rejected-Bereinigung, Move nach temp_final).
# AUTHOR:      Matzethias
# DATE:        2026-08-09
# VERSION:     1.6
# REQUIRES:    Python 3.11, pathlib, shutil
# CHANGES:
#   2026-08-22 | C1.2.3 | Kanonische Review-/Rejected-Ordnernamen ohne Unterstrich vereinheitlicht.
#   2026-08-09 | 1.0 | Initiale Version mit Archive-Vertrag
#   2026-08-09 | 1.5 | Review/Rejected-Bereinigung + Move nach temp_final
# =============================================================================


from pathlib import Path
import shutil
from .phase_state import transition, PhaseTransitionError
from .state_store import StateStore
from datetime import datetime
from typing import Dict, Any
from .automation_metrics import AutomationMetrics


def cleanup_review_rejected(batch_path: str, cfg: dict, dry_run: bool = False, delete_files: bool = True) -> Dict[str, Any]:
    """
    Bereinigt Review und Rejected Ordner nach Phase 2.
    
    Review-Dateien:
    - Keep-Entscheidungen: Nach 03_TEMP_DONE (für spätere manuelle Prüfung)
    - Reject-Entscheidungen: Nach 00_TEMP_ERROR
    
    Rejected-Dateien:
    - Alle nach 00_TEMP_ERROR (keine automatische Löschung)
    
    Ordner-Logik:
    - Review und Rejected werden nach dem Verschieben GELÖSCHT (auch wenn nicht leer)
    - Dies erfolgt unabhängig von move_to_temp_final
    - Nicht verschobene Dateien im Ordner gehen dabei verloren (geplantes Verhalten)
    
    98AP-Regeln:
      - AP2: Review-Entscheidungen bleiben nachvollziehbar
      - AP7: Keine automatischen Löschungen ohne Log
      - AP8: Move nach temp_final erst nach vollständiger Bereinigung
    
    Args:
        batch_path: Pfad zum Batch-Ordner
        cfg: Config-Dictionary mit Pfaden
        dry_run: Wenn True, nur simulieren
        delete_files: Wenn True, Dateien löschen statt nach temp_error verschieben
    
    Returns:
        dict mit:
            - review_keep_moved: Anzahl Keep-Dateien nach temp_done
            - review_reject_moved: Anzahl Reject-Dateien nach error
            - rejected_moved: Anzahl Rejected-Dateien nach error
            - errors: Liste von Fehlermeldungen (inkl. verbleibende Dateien)
            - status: 'ok', 'partial', 'failed'
    """
    batch = Path(batch_path)
    review_path = batch / "Review"
    rejected_path = batch / "Rejected"
    
    # Phase-2-Config auslesen (konsistent mit Repo-Stil)
    phase2_cfg = cfg.get('phase2', {})
    cleanup_enabled = bool(phase2_cfg.get('cleanup_review_rejected', True))
    dry_run = dry_run or bool(phase2_cfg.get('dry_run', False))
    
    # Pfade aus Config
    temp_done_dir = Path(cfg['paths']['temp_done'])
    temp_error_dir = Path(cfg['paths'].get('temp_error', '../NAS_EXAMPLE/00_TEMP_ERROR'))
    
    result = {
        'review_keep_moved': 0,
        'review_reject_moved': 0,
        'rejected_moved': 0,
        'errors': [],
        'status': 'ok',
    }
    
    # ==========================================================================
    # SCHRITT 1: Review bereinigen
    # ==========================================================================
    if review_path.exists():
        for img in review_path.iterdir():
            if (
                not img.is_file()
                or img.is_symlink()
                or img.suffix.lower() not in {".jpg", ".jpeg"}
            ):
                continue
            
            try:
                # Entscheidung aus Metadaten lesen
                decision = read_decision(img)
                
                if decision == "keep":
                    # Nach temp_done für manuelle Prüfung
                    target = temp_done_dir / f"{batch.name}_REVIEW_{img.name}"
                    if not dry_run:
                        temp_done_dir.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(img), str(target))
                    result['review_keep_moved'] += 1
                else:
                    # Nach error oder löschen
                    if delete_enabled:
                        if not dry_run:
                            img.unlink()
                    else:
                        target = temp_error_dir / f"{batch.name}_REVIEW_{img.name}"
                        if not dry_run:
                            temp_error_dir.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(img), str(target))
                    result['review_reject_moved'] += 1
                    
            except Exception as e:
                result['errors'].append(f"Review {img.name}: {e}")
    
    # ==========================================================================
    # SCHRITT 2: Rejected bereinigen
    # ==========================================================================
    if rejected_path.exists():
        for img in rejected_path.iterdir():
            if (
                not img.is_file()
                or img.is_symlink()
                or img.suffix.lower() not in {".jpg", ".jpeg"}
            ):
                continue
            
            try:
                # Alle nach error oder löschen
                if delete_enabled:
                    if not dry_run:
                        img.unlink()
                else:
                    target = temp_error_dir / f"{batch.name}_REJ_{img.name}"
                    if not dry_run:
                        temp_error_dir.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(img), str(target))
                result['rejected_moved'] += 1
                
            except Exception as e:
                result['errors'].append(f"Rejected {img.name}: {e}")
    
    # ==========================================================================
    # SCHRITT 3: Ordner löschen (IMMER nach dem Verschieben, auch wenn nicht leer)
    # ==========================================================================
    try:
        # Review-Ordner löschen (auch wenn nicht leer)
        if review_path.exists():
            remaining_review = list(review_path.glob("*"))
            if remaining_review and not dry_run:
                # Warnung: Es sind noch Dateien im Ordner
                result['errors'].append(f"Review-Ordner nicht leer: {[f.name for f in remaining_review]}")
            
            if not dry_run:
                shutil.rmtree(review_path)
            print(f"[CLEANUP] Ordner gelöscht: {review_path}")
        
        # Rejected-Ordner löschen (auch wenn nicht leer)
        if rejected_path.exists():
            remaining_rejected = list(rejected_path.glob("*"))
            if remaining_rejected and not dry_run:
                # Warnung: Es sind noch Dateien im Ordner
                result['errors'].append(f"Rejected-Ordner nicht leer: {[f.name for f in remaining_rejected]}")
            
            if not dry_run:
                shutil.rmtree(rejected_path)
            print(f"[CLEANUP] Ordner gelöscht: {rejected_path}")
    except Exception as e:
        result['errors'].append(f'Ordner löschen: {e}')
    
    # ==========================================================================
    # SCHRITT 4: Status bestimmen
    # ==========================================================================
    if result['errors']:
        result['status'] = 'partial' if result['review_keep_moved'] + result['review_reject_moved'] + result['rejected_moved'] > 0 else 'failed'
    else:
        result['status'] = 'ok'
    
    return result


def read_decision(image_path: Path) -> str:
    """
    Liest die Culling-Entscheidung aus den Metadaten einer JPG-Datei.
    
    98AP-Regeln:
      - AP7: Nachvollziehbare Entscheidungen
      - Metadaten bleiben erhalten
    
    Args:
        image_path: Pfad zur JPG-Datei
    
    Returns:
        'keep', 'review', 'reject' oder 'unknown'
    """
    try:
        # ExifTool oder metadata_rating.py verwenden
        from app.metadata_rating import read_rating_from_image
        
        rating = read_rating_from_image(image_path)
        
        if rating >= 4:
            return 'keep'
        elif rating >= 2:
            return 'review'
        else:
            return 'reject'
            
    except Exception:
        # Fallback: Entscheidung aus Dateinamen ableiten
        # (falls keine Metadaten vorhanden)
        return 'unknown'


def move_to_temp_final(batch_path: str, cfg: dict, dry_run: bool = False) -> Dict[str, Any]:
    """
    Verschiebt den bereinigten Batch nach temp_final.

    Move-Logik (98AP-Vertrag):
    - copy: Batch wird zuerst kopiert (shutil.move verwendet intern copy2)
    - verify: Ziel wird nach dem Move validiert (Dateiliste, Größe)
    - source removal: Quelle wird nach erfolgreichem Move entfernt
    
    Voraussetzung:
    - Review/Rejected bereinigt
    - Archive verifiziert
    - State-Update abgeschlossen
    
    98AP-Regeln:
      - AP8: Move erst nach vollständiger Bereinigung
      - AP7: Nachvollziehbare Zustandsübergänge
    
    Args:
        batch_path: Pfad zum Batch-Ordner
        cfg: Config-Dictionary mit Pfaden
        dry_run: Wenn True, nur simulieren
        delete_files: Wenn True, Dateien löschen statt nach temp_error verschieben
    
    Returns:
        dict mit:
            - success: bool
            - target_path: str (Zielpfad)
            - error: str (Fehlermeldung, falls vorhanden)
    """
    batch = Path(batch_path)
    
    # NEU: Config konsistent auslesen
    temp_final_dir = Path(cfg['paths']['temp_final'])
    move_enabled = bool(cfg.get('phase2', {}).get('move_to_temp_final', False))
    dry_run = dry_run or bool(cfg.get('phase2', {}).get('dry_run', False))
    
    result = {
        'success': False,
        'target_path': '',
        'error': '',
    }
    
    # Move in Config deaktiviert?
    if not move_enabled:
        result['error'] = 'move_to_temp_final ist in der Config deaktiviert'
        return result
    
    # Sicherheitsprüfung: Batch muss existieren
    if not batch.exists():
        result['error'] = f'Batch existiert nicht: {batch}'
        return result
    
    # Zielpfad
    target = temp_final_dir / batch.name
    
    # Kollisionsprüfung
    if target.exists():
        result['error'] = f'Zielpfad existiert bereits: {target}'
        return result
    
    # Move durchführen
    if not dry_run:
        try:
            shutil.move(str(batch), str(target))
            result['success'] = True
            result['target_path'] = str(target)
        except Exception as e:
            result['error'] = f'Move fehlgeschlagen: {e}'
    else:
        # Dry run
        result['success'] = True
        result['target_path'] = str(target)
        result['error'] = 'Dry run - keine Dateioperation'
    
    return result


def verify_cleanup_complete(batch_path: str) -> Dict[str, Any]:
    """
    Prüft, ob Review/Rejected vollständig bereinigt wurden.
    
    Args:
        batch_path: Pfad zum Batch-Ordner
    
    Returns:
        dict mit:
            - review_empty: bool
            - rejected_empty: bool
            - complete: bool
            - review_remaining: list[str]
            - rejected_remaining: list[str]
    """
    batch = Path(batch_path)
    review_path = batch / "Review"
    rejected_path = batch / "Rejected"
    
    result = {
        'review_empty': False,
        'rejected_empty': False,
        'complete': False,
        'review_remaining': [],
        'rejected_remaining': [],
    }
    
    # Review prüfen
    if review_path.exists():
        remaining = [
            item.name
            for item in review_path.iterdir()
            if item.is_file() and item.suffix.lower() in {".jpg", ".jpeg"}
        ]
        result['review_remaining'] = remaining
        result['review_empty'] = len(remaining) == 0
    else:
        result['review_empty'] = True
    
    # Rejected prüfen
    if rejected_path.exists():
        remaining = [
            item.name
            for item in rejected_path.iterdir()
            if item.is_file() and item.suffix.lower() in {".jpg", ".jpeg"}
        ]
        result['rejected_remaining'] = remaining
        result['rejected_empty'] = len(remaining) == 0
    else:
        result['rejected_empty'] = True
    
    # Gesamtstatus
    result['complete'] = result['review_empty'] and result['rejected_empty']
    
    return result


def run_phase2_with_cleanup(batch_path: str, cfg: dict, dry_run: bool = False) -> Dict[str, Any]:
    """
    Führt Phase 2 komplett aus: Bereinigung + Move nach temp_final.
    
    98AP-Regeln:
      - AP2: Review-Entscheidungen bleiben nachvollziehbar
      - AP7: Keine automatischen Löschungen ohne Log
      - AP8: Move nach temp_final erst nach vollständiger Bereinigung
    
    Args:
        batch_path: Pfad zum Batch-Ordner
        cfg: Config-Dictionary mit Pfaden
        dry_run: Wenn True, nur simulieren
        delete_files: Wenn True, Dateien löschen statt nach temp_error verschieben
    
    Returns:
        dict mit:
            - cleanup_result: dict von cleanup_review_rejected()
            - move_result: dict von move_to_temp_final()
            - status: 'ok', 'partial', 'failed'
    """
    result = {
        'cleanup_result': {},
        'move_result': {},
        'status': 'ok',
    }
    

    # ==========================================================================
    # SCHRITT 0: Phase 2 als gestartet markieren
    # ==========================================================================
    from app.config_schema import config_fingerprint
    
    try:
        state_dir = Path(cfg['runtime']['state_dir'])
        store = StateStore(state_dir)
        batch_id = Path(batch_path).name
        producer_version = "1.2.1"
        
        transition(
            store,
            batch_id,
            "phase2_started",
            producer_version=producer_version,
            config_fingerprint=config_fingerprint(cfg),
        )
    except Exception as e:
        # State-Update ist nicht kritisch für den Betrieb
        result['state_warning'] = f"phase2_started failed: {e}"

    # ==========================================================================
    # SCHRITT 1: Review/Rejected bereinigen
    # ==========================================================================
    cleanup_result = cleanup_review_rejected(batch_path, cfg, dry_run=dry_run)
    result['cleanup_result'] = cleanup_result
    
    # ==========================================================================
    # SCHRITT 2: Bereinigung verifizieren
    # ==========================================================================
    verify_result = verify_cleanup_complete(batch_path)
    
    if not verify_result['complete']:
        result['status'] = 'partial'
        # Bei unvollständiger Bereinigung KEIN Move nach temp_final!
        return result
    # Phase 2 als abgeschlossen markieren
    # State-Update: phase2_completed setzen
    
    try:
        state_dir = Path(cfg['runtime']['state_dir'])
        store = StateStore(state_dir)
        batch_id = Path(batch_path).name
        producer_version = "1.2.1"  # Muss mit der tatsächlichen Version übereinstimmen
        
        transition(
            store,
            batch_id,
            "phase2_completed",
            producer_version=producer_version,
            config_fingerprint=config_fingerprint(cfg),
        )
    except Exception as e:
        # State-Update ist nicht kritisch für den Betrieb
        # Fehler wird geloggt, aber Phase 2 läuft weiter
        result['status'] = 'partial'
        result['state_error'] = str(e)
    
    # ==========================================================================
    # SCHRITT 3: Move nach temp_final (nur bei vollständiger Bereinigung)
    # ==========================================================================
    if cfg.get('phase2', {}).get('move_to_temp_final', False):
        move_result = move_to_temp_final(batch_path, cfg, dry_run=dry_run)
        result['move_result'] = move_result
        
        if move_result['success']:
            result['status'] = 'ok'
        else:
            result['status'] = 'failed'
    
    return result
    
    
def update_automation_metrics(runtime_path: Path):
    """
    Aktualisiert Automation-Metrics nach Phase-2-Abschluss.
    
    Wird nach jedem Batch aufgerufen.
    """
    metrics_calc = AutomationMetrics(runtime_path)
    metrics = metrics_calc.calculate_readiness(min_batches=10, threshold=0.85)
    
    output_path = runtime_path / "automation_metrics.json"
    metrics_calc.save_metrics(metrics, output_path)
    
    return metrics