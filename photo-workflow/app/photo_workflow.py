"""
Skript: app/photo_workflow.py
Zweck: Haupt-Entry-Point für Photo Workflow mit AI Culling, Face-Erkennung und MANUAL_KEEP.
Autor: MaiTaiMa
Erstellt: 2026-08-09
Version: 1.4
Requires: Python 3.11, OpenCV-Contrib, NumPy, PyYAML, ExifTool

Änderungsprotokoll:
  2026-08-09 | 1.0 | Initiale Version mit Phase 1/2
  2026-08-09 | 1.3 | Face-Erkennung und AI Culling ergänzt
  2026-08-09 | 1.4 | MANUAL_KEEP-Integration, dynamische Face-Erkennung, Terminal-Ausgabe
"""

from __future__ import annotations

# === Standardbibliothek ===
# Zweck: Batch-Verarbeitung, Datei-Operationen, Logging, Konfiguration.
# Eingabe: Config, Batch-Pfade, Bild-Dateien.
# Ausgabe: Culling-Entscheidungen, Metadaten, Reports, Terminal-Ausgabe.
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import time
import zipfile
import yaml

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

# === App-Imports ===
from app.automation_config import validate_automation_config
from app.auto_decision import predict_decision
from app.automation_contract import build_prediction_record

from app.aesthetic import (
    base_score_components,
    ensure_reference_profile,
    generic_aesthetic_score,
    load_personal_model,
    personal_model_score,
    weighted_base_score,
)

from app.family_recognition import (
    detect_family_members,
    load_family_model,
    rebuild_family_cache,
    write_native_tags,
)

from app.manual_keep import (
    detect_manual_keep_images,
    move_manual_keep_sources_to_used,
)

from app.series_culling import apply_series_culling
from app.metadata_writer import write_culling_metadata
from app.training import train_from_directory, load_or_rebuild_personal_model

# === Konstanten ===
RAW_EXTS = {'.ARW', '.arw'}
JPG_EXTS = {'.JPG', '.jpg', '.JPEG', '.jpeg'}
RAW_PATTERN = re.compile(r'^\d{8}$')
DONE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}(_.*)?$')

# === Globale Zähler ===
COUNT_PROCESSED = 0
COUNT_MOVED = 0
COUNT_SKIPPED = 0
COUNT_ERRORS = 0
COUNT_FOUND_SRC = 0
COUNT_FOUND_DONE = 0
LAST_FAMILY_RUN_INFO = {}
LAST_ZIP_CONFLICTS: list[dict] = []

# === Script-Metadaten ===
SCRIPT_NAME = 'Synology Photo Workflow with AI Culling'
SCRIPT_VERSION = 'v1.4'
SCRIPT_DESCRIPTION = 'Processes TEMP_SD, moves folders to TEMP_IMAGES, post-processes TEMP_DONE, adds AI-assisted JPG culling, optional family face tagging, MANUAL_KEEP support, and cached family encodings.'

def now() -> str:
    """Gibt den aktuellen UTC-Zeitpunkt im ISO-8601-Format zurück."""
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def reset_counters() -> None:
    """Setzt alle globalen Zähler für einen neuen Lauf zurück."""
    global COUNT_PROCESSED, COUNT_MOVED, COUNT_SKIPPED, COUNT_ERRORS, COUNT_FOUND_SRC, COUNT_FOUND_DONE, LAST_FAMILY_RUN_INFO, LAST_ZIP_CONFLICTS
    COUNT_PROCESSED = 0
    COUNT_MOVED = 0
    COUNT_SKIPPED = 0
    COUNT_ERRORS = 0
    COUNT_FOUND_SRC = 0
    COUNT_FOUND_DONE = 0
    LAST_FAMILY_RUN_INFO = {}
    LAST_ZIP_CONFLICTS = []


def load_config(path: str | Path) -> dict:
    """
    Lädt und validiert die Config-Datei mit Default-Werten.
    
    98AP-Regeln:
      - Config bleibt secrets-frei (keine API-Keys, Tokens)
      - Unbekannte Schlüssel sind Fehler außer `extensions`
      - Config-Schlüssel durchgängig snake_case
    """
    cfg = yaml.safe_load(Path(path).read_text(encoding='utf-8'))

    # Paths-Defaults
    cfg.setdefault('paths', {})
    cfg['paths'].setdefault('manual_keep_inbox', str(Path(cfg['paths']['base_dir']) / 'MANUAL_KEEP' / 'inbox'))
    cfg['paths'].setdefault('manual_keep_used', str(Path(cfg['paths']['base_dir']) / 'MANUAL_KEEP' / 'used'))

    # Reporting-Defaults
    cfg.setdefault('reporting', {})
    cfg['reporting'].setdefault('write_json_summary', True)
    cfg['reporting'].setdefault('json_summary_dir', str(Path(cfg['paths']['base_dir']) / 'run_summaries'))
    cfg['reporting'].setdefault('stdout_mode', 'scheduler_mail')

    # Workflow-Defaults
    cfg.setdefault('workflow', {})
    wf = cfg['workflow']
    wf.setdefault('wait_time_seconds', 60)
    wf.setdefault('stale_lock_seconds', 43200)
    wf.setdefault('merge_strategy', 'merge_then_fallback')
    wf.setdefault('create_done_marker_before_move', True)
    wf.setdefault('date_reconstruction', {})
    dr = wf['date_reconstruction']
    dr.setdefault('mode', 'legacy_bash')
    dr.setdefault('decade_prefix', '202')
    dr.setdefault('year_digit_index', 3)

    # Family-Recognition-Defaults
    cfg.setdefault('family_recognition', {})
    fr = cfg['family_recognition']
    fr.setdefault('enabled', False)
    fr.setdefault('reference_dir', str(Path(cfg['paths']['base_dir']) / 'family_faces'))
    fr.setdefault('cache_enabled', True)
    fr.setdefault('cache_dir', str(Path(cfg['paths']['base_dir']) / 'models' / 'family_faces'))
    fr.setdefault('cache_rebuild_mode', 'incremental')
    fr.setdefault('force_cache_rebuild', False)
    fr.setdefault('protect_detected_family', True)
    fr.setdefault('score_boost_weight', 0.20)
    fr.setdefault('write_native_tags', True)
    fr.setdefault('write_face_regions', False)
    fr.setdefault('exiftool_path', 'exiftool')
    fr.setdefault('match_tolerance', 0.48)
    fr.setdefault('default_person_weight', 0.35)
    fr.setdefault('min_reference_images_per_person', 3)
    fr.setdefault('max_reference_images_per_person', 200)
    fr.setdefault('person_weights', {})

    # Series-Detection-Defaults
    cfg.setdefault('series_detection', {})
    sd = cfg['series_detection']
    sd.setdefault('enabled', True)
    sd.setdefault('cluster_eps', 0.18)
    sd.setdefault('min_samples', 2)
    sd.setdefault('preview_size', 32)
    sd.setdefault('review_margin', 0.03)
    sd.setdefault('demote_non_best_to', 'review')

    # Metadata-Culling-Defaults
    cfg.setdefault('metadata_culling', {})
    mc = cfg['metadata_culling']
    mc.setdefault('enabled', True)
    mc.setdefault('write_rating', True)
    mc.setdefault('write_keywords', True)
    mc.setdefault('keep_backup', False)
    mc.setdefault('exiftool_path', 'exiftool')
    mc.setdefault('rating_map', {'keep': 5, 'review': 3, 'reject': 0})

    # Culling-Defaults
    cfg.setdefault('culling', {})
    cull = cfg['culling']
    cull.setdefault('enabled', True)
    cull.setdefault('move_files', True)
    cull.setdefault('create_review_folder', True)
    cull.setdefault('create_rejected_folder', True)
    cull.setdefault('keep_threshold', 0.65)
    cull.setdefault('reject_threshold', 0.35)
    cull.setdefault('weights', {'generic': 0.55, 'personal': 0.45})
    cull.setdefault('component_weights', {'base_score': 0.55, 'eye_score': 0.10, 'personal_score': 0.20, 'family_score': 0.15})
    cull.setdefault('base_weights', {'sharp': 0.36, 'aesth': 0.36, 'exposure': 0.18, 'reference': 0.10})
    cull.setdefault('eye_detection', {'enabled': True})
    cull.setdefault('reference_scoring', {'enabled': False, 'folder': str(Path(cfg['paths']['base_dir']) / 'reference_images'), 'recursive': False, 'preview_size': 32, 'cache_enabled': True, 'cache_dir': str(Path(cfg['paths']['base_dir']) / 'models' / 'reference_scoring'), 'force_cache_rebuild': False})
    cull.setdefault('star_rating_bands', {5: 0.90, 4: 0.75, 3: 0.60, 2: 0.40, 1: 0.20, 0: 0.00})

    # Personal-Scoring-Defaults
    personal_cfg = cfg.setdefault('personal_scoring', {})
    personal_cfg.setdefault('enabled', True)
    personal_cfg.setdefault('source_dir', cfg.get('training', {}).get('sample_images_dir', cull.get('reference_scoring', {}).get('folder', str(Path(cfg['paths']['base_dir']) / 'reference_images'))))
    personal_cfg.setdefault('model_path', cfg['paths'].get('personal_model', str(Path(cfg['paths']['base_dir']) / 'models' / 'personal' / 'user_taste_model.json')))
    personal_cfg.setdefault('cache_enabled', True)
    personal_cfg.setdefault('cache_dir', str(Path(personal_cfg['model_path']).parent))
    personal_cfg.setdefault('cache_rebuild_mode', 'incremental')
    personal_cfg.setdefault('force_cache_rebuild', False)
    personal_cfg.setdefault('auto_train_on_change', True)
    personal_cfg.setdefault('recursive', False)
    personal_cfg.setdefault('min_reference_images', 5)

    # Metadata-Keyword-Schema
    metadata_cfg = cfg.setdefault('metadata_culling', {})
    metadata_cfg.setdefault('keyword_schema', 'namespaced_v1')
    metadata_cfg.setdefault('write_score_bands', True)
    metadata_cfg.setdefault('write_raw_scores_to_keywords', False)

    # Automation-Defaults und Validierung
    cfg.setdefault('automation', {})
    automation = cfg['automation']
    automation.setdefault('mode', 'shadow')
    automation.setdefault('keep_score_min', 0.90)
    automation.setdefault('reject_score_max', 0.15)
    automation.setdefault('evaluation_window_days', 90)
    automation.setdefault('min_evaluated_batches', 10)
    automation.setdefault('min_evaluated_images', 500)
    automation.setdefault('min_overall_agreement', 0.85)
    automation.setdefault('min_keep_precision', 0.95)
    automation.setdefault('min_reject_precision', 0.98)

    cfg['automation'] = validate_automation_config(cfg)

    return cfg


def log(cfg: dict, message: str, error: bool = False) -> None:
    """Schreibt eine Log-Zeile in die Config-definierte Log-Datei."""
    target = Path(cfg['paths']['error_log'] if error else cfg['paths']['log_file'])
    target.parent.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n"
    with target.open('a', encoding='utf-8') as handle:
        handle.write(line)
    print(line, end='', file=sys.stderr if error else sys.stdout)
    
def print_start_banner(cfg: dict, command: str) -> None:
    """Druckt den Start-Banner für den Workflow."""
    print(f"===== START: {datetime.now()} =====")
    print(f"SCRIPT : {SCRIPT_NAME}")
    print(f"VERSION : {SCRIPT_VERSION}")
    print(f"COMMAND : {command}")
    print(f"PURPOSE : {SCRIPT_DESCRIPTION}")
    print(f"BASE_DIR : {cfg['paths']['base_dir']}")
    print(f"SRC : {cfg['paths']['temp_sd']}")
    print(f"DEST : {cfg['paths']['temp_images']}")
    print(f"DONE : {cfg['paths']['temp_done']}")
    print('========================================')


def build_summary_payload(cfg: dict, command: str, status: str, started_at: str, finished_at: str, json_summary_path: str | None) -> dict:
    """Erstellt den Summary-Payload für JSON-Report und Terminal-Ausgabe."""
    return {
        'script_name': SCRIPT_NAME,
        'script_version': SCRIPT_VERSION,
        'command': command,
        'status': status,
        'started_at': started_at,
        'finished_at': finished_at,
        'paths': {
            'base_dir': cfg['paths']['base_dir'],
            'temp_sd': cfg['paths']['temp_sd'],
            'temp_images': cfg['paths']['temp_images'],
            'temp_done': cfg['paths']['temp_done'],
            'log_file': cfg['paths']['log_file'],
            'error_log': cfg['paths']['error_log'],
        },
        'counts': {
            'found_temp_sd': COUNT_FOUND_SRC,
            'found_temp_done': COUNT_FOUND_DONE,
            'processed': COUNT_PROCESSED,
            'moved_merged': COUNT_MOVED,
            'skipped': COUNT_SKIPPED,
            'errors': COUNT_ERRORS,
        },
        'family_recognition': LAST_FAMILY_RUN_INFO,
        'zip_conflicts': LAST_ZIP_CONFLICTS,
        'json_summary_path': json_summary_path,
    }


def write_json_summary(cfg: dict, payload: dict) -> str | None:
    """Schreibt eine JSON-Zusammenfassung des Laufs."""
    if not cfg['reporting'].get('write_json_summary', True):
        return None
    summary_dir = Path(cfg['reporting']['json_summary_dir'])
    summary_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = summary_dir / f"{payload['command']}_{timestamp}.json"
    payload = dict(payload)
    payload['json_summary_path'] = str(path)
    path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    return str(path)


def print_scheduler_summary(cfg: dict, payload: dict) -> None:
    """Druckt die Scheduler-Zusammenfassung auf dem Terminal."""
    print('SUMMARY')
    print(f"Status: {payload['status']}")
    print(f"Command: {payload['command']}")
    print(f"Found folders in TEMP_SD: {payload['counts']['found_temp_sd']}")
    print(f"Found folders in TEMP_DONE: {payload['counts']['found_temp_done']}")
    print(f"Processed folders: {payload['counts']['processed']}")
    print(f"Moved/Merged: {payload['counts']['moved_merged']}")
    print(f"Skipped folders: {payload['counts']['skipped']}")
    print(f"Errors: {payload['counts']['errors']}")
    if payload.get('family_recognition'):
        print(f"Family recognition: {payload['family_recognition']}")
    print(f"Log file: {payload['paths']['log_file']}")
    print(f"Error log: {payload['paths']['error_log']}")
    if payload.get('json_summary_path'):
        print(f"JSON summary: {payload['json_summary_path']}")
    print(f"Started: {payload['started_at']}")
    print(f"Finished: {payload['finished_at']}")
    print('===== END =====')


def ensure_dir(path: str | Path) -> Path:
    """Stellt sicher, dass ein Verzeichnis existiert."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def path_within(base: Path, target: Path) -> bool:
    """Prüft, ob target innerhalb von base liegt."""
    try:
        target.resolve().relative_to(base.resolve())
        return True
    except Exception:
        return False


def require_within(cfg: dict, target: Path) -> None:
    """Erzwingt, dass target innerhalb von base_dir liegt (98AP-AP2)."""
    if not cfg['safety'].get('require_paths_within_base_dir', True):
        return
    base = Path(cfg['paths']['base_dir']).resolve()
    if not path_within(base, target):
        raise ValueError(f'Path escapes base_dir: {target}')
        
def run_pipeline(cfg: dict, folder: str | None = None) -> None:
    """
    Führt eine Pipeline von Phasen aus (konfigurierbar).
    
    98AP-Regeln:
      - AP7: Nachvollziehbare Zustandsübergänge
      - AP8: Phasen dürfen nur in definierter Reihenfolge ausgeführt werden
    
    Args:
        cfg: Config-Dictionary
        folder: Optionaler spezifischer Batch-Ordner
    """
    pipeline_cfg = cfg.get('pipeline', {})
    phases = pipeline_cfg.get('phases', ['phase1', 'phase2'])
    stop_on_error = bool(pipeline_cfg.get('stop_on_error', True))
    
    log(cfg, f'[PIPELINE] Starte Pipeline mit Phasen: {phases}')
    
    for phase in phases:
        log(cfg, f'[PIPELINE] === Phase: {phase} ===')
        
        try:
            if phase == 'phase1':
                run_phase1(cfg, folder)
            elif phase == 'phase2':
                run_phase2(cfg, folder)
            elif phase == 'phase3':  # Zukünftig
                # run_phase3(cfg, folder)  # Noch nicht implementiert
                log(cfg, f'[PIPELINE] Phase {phase} noch nicht implementiert', error=True)
            elif phase == 'train-personal':
                run_training(cfg, None, None)
            elif phase == 'rebuild-family-cache':
                run_family_cache_rebuild(cfg)
            else:
                log(cfg, f'[PIPELINE] Unbekannte Phase: {phase}', error=True)
                
        except Exception as exc:
            log(cfg, f'[PIPELINE] Phase {phase} fehlgeschlagen: {exc}', error=True)
            
            if stop_on_error:
                log(cfg, f'[PIPELINE] Pipeline abgebrochen (stop_on_error=true)', error=True)
                return
    
    log(cfg, f'[PIPELINE] Pipeline erfolgreich abgeschlossen')
        
@contextmanager
def file_lock(cfg: dict):
    """
    Setzt einen globalen Lock für produktive Läufe.
    
    98AP-Regeln:
      - Parallele produktive Läufe werden verhindert
      - Stale Locks (> stale_lock_seconds) werden bereinigt
    """
    lock_path = Path(cfg['paths']['lock_file'])
    ensure_dir(lock_path.parent)
    stale_seconds = int(cfg['workflow'].get('stale_lock_seconds', 43200))

    if lock_path.exists():
        try:
            data = json.loads(lock_path.read_text(encoding='utf-8'))
            started_at = str(data['started_at']).replace('Z', '+00:00')
            ts = datetime.fromisoformat(started_at).timestamp()
            if time.time() - ts > stale_seconds:
                lock_path.unlink()
            else:
                raise RuntimeError(f'Active lock file present: {lock_path}')
        except RuntimeError:
            raise
        except Exception:
            raise RuntimeError(f'Active lock file present: {lock_path}')

    lock_path.write_text(json.dumps({'pid': os.getpid(), 'started_at': now()}), encoding='utf-8')

    try:
        yield
    finally:
        if lock_path.exists():
            lock_path.unlink()


def make_date_name(name: str, cfg: dict) -> str:
    """Rekonstruiert ein Datum aus einem Batch-Namen."""
    if not RAW_PATTERN.match(name):
        return name

    date_cfg = cfg.get('workflow', {}).get('date_reconstruction', {})
    mode = str(date_cfg.get('mode', 'legacy_bash')).strip().lower()

    if mode == 'legacy_bash':
        decade_prefix = str(date_cfg.get('decade_prefix', '202')).strip()
        year_digit_index = int(date_cfg.get('year_digit_index', 3))

        if not re.fullmatch(r'\d{3}', decade_prefix):
            raise ValueError(f'workflow.date_reconstruction.decade_prefix must be exactly 3 digits, got: {decade_prefix!r}')
        if not 0 <= year_digit_index < len(name):
            raise ValueError(f'workflow.date_reconstruction.year_digit_index out of range: {year_digit_index}')

        year = f"{decade_prefix}{name[year_digit_index]}"
        month, day = name[4:6], name[6:8]
        return f'{year}-{month}-{day}'

    if mode == 'full_year':
        return f'{name[0:4]}-{name[4:6]}-{name[6:8]}'

    raise ValueError(f'Unsupported workflow.date_reconstruction.mode: {mode}')


def classify_zip_artifact(zip_path: Path) -> str:
    """Klassifiziert ein ZIP-Artefakt nach Typ."""
    name = zip_path.name
    if name.endswith('_ALL_JPG.zip') or '_ALL_JPG_EXTRA_' in name:
        return 'all_jpg'
    if name.endswith('_SORT_ARW.zip') or '_SORT_ARW_EXTRA_' in name:
        return 'sort_arw'

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            file_names = [n for n in zf.namelist() if not n.endswith('/')]
    except zipfile.BadZipFile:
        return 'unsorted'

    if file_names and all(Path(n).suffix.lower() in {'.jpg', '.jpeg'} for n in file_names):
        return 'all_jpg'
    if file_names and all(Path(n).suffix.lower() in {'.arw'} for n in file_names):
        return 'sort_arw'

    return 'unsorted'


def next_available_artifact_path(save_dir: Path, folder_name: str, artifact_type: str) -> Path:
    """Generiert einen eindeutigen Pfad für ein ZIP-Artefakt."""
    if artifact_type == 'all_jpg':
        base = save_dir / f'{folder_name}_ALL_JPG.zip'
        extra_template = f'{folder_name}_ALL_JPG_EXTRA_{{}}.zip'
    elif artifact_type == 'sort_arw':
        base = save_dir / f'{folder_name}_SORT_ARW.zip'
        extra_template = f'{folder_name}_SORT_ARW_EXTRA_{{}}.zip'
    else:
        idx = 1
        target = save_dir / f'{folder_name}_UNSORTED_{idx}.zip'
        while target.exists():
            idx += 1
            target = save_dir / f'{folder_name}_UNSORTED_{idx}.zip'
        return target

    if not base.exists():
        return base

    idx = 2
    target = save_dir / extra_template.format(idx)
    while target.exists():
        idx += 1
        target = save_dir / extra_template.format(idx)

    return target


def preserve_zip_artifact(zip_path: Path, save_dir: Path, folder_name: str, cfg: dict | None = None) -> Path:
    """Bewahrt ein ZIP-Artefakt mit Kollisionsvermeidung auf."""
    artifact_type = classify_zip_artifact(zip_path)
    target = next_available_artifact_path(save_dir, folder_name, artifact_type)

    if zip_path.resolve() == target.resolve():
        return zip_path

    if target.exists():
        raise FileExistsError(f'Target ZIP path already exists: {target}')

    zip_path.rename(target)

    if cfg is not None and target.name != zip_path.name:
        entry = {
            'folder': folder_name,
            'source_name': zip_path.name,
            'target_name': target.name,
            'artifact_type': artifact_type,
            'collision_avoided': '_EXTRA_' in target.name or '_UNSORTED_' in target.name,
        }
        LAST_ZIP_CONFLICTS.append(entry)
        log(cfg, f'[ZIP PRESERVE] {zip_path.name} -> {target.name} ({artifact_type})')

    return target


def is_valid_raw_folder(name: str) -> bool:
    """Prüft, ob ein Batch-Name dem RAW-Muster entspricht."""
    return bool(RAW_PATTERN.match(name))


def is_valid_done_folder(name: str) -> bool:
    """Prüft, ob ein Batch-Name dem DONE-Muster entspricht."""
    return bool(DONE_PATTERN.match(name))


def is_stable(folder: Path, wait_seconds: int) -> bool:
    """Prüft, ob ein Batch stabil ist (keine Änderungen während wait_seconds)."""
    def snapshot() -> list[tuple[str, int]]:
        rows = []
        for p in sorted(folder.rglob('*')):
            if p.is_symlink():
                continue
            if p.is_file():
                rows.append((str(p.relative_to(folder)), p.stat().st_size))
        return rows

    s1 = snapshot()
    time.sleep(wait_seconds)
    s2 = snapshot()
    return s1 == s2


def top_level_files(folder: Path, suffixes: set[str]) -> list[Path]:
    """Gibt alle Dateien auf oberster Ebene mit bestimmten Suffixes zurück."""
    return sorted([p for p in folder.iterdir() if p.is_file() and p.suffix in suffixes])


def top_level_jpgs(folder: Path) -> list[Path]:
    """Gibt alle JPGs auf oberster Ebene zurück."""
    return top_level_files(folder, JPG_EXTS)


def top_level_arws(folder: Path) -> list[Path]:
    """Gibt alle ARWs auf oberster Ebene zurück."""
    return top_level_files(folder, RAW_EXTS)


def create_zip(zip_path: Path, files: list[Path]) -> None:
    """Erstellt ein ZIP-Archiv aus einer Dateiliste."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = zip_path.with_suffix(zip_path.suffix + '.tmp')
    if tmp.exists():
        tmp.unlink()

    with zipfile.ZipFile(tmp, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            zf.write(file, arcname=file.name)

    tmp.replace(zip_path)
    
def resolve_merge_fallback_dir(dest: Path) -> Path:
    """Generiert einen Fallback-Namen für Merge-Kollisionen."""
    candidate = Path(str(dest) + '_MERGE')
    if not candidate.exists():
        return candidate

    i = 2
    while True:
        candidate = Path(str(dest) + f'_MERGE_{i}')
        if not candidate.exists():
            return candidate
        i += 1


def merge_or_move_folder(src: Path, dest: Path, cfg: dict) -> Path:
    """Verschiebt oder merged einen Batch-Ordner."""
    global COUNT_MOVED, COUNT_ERRORS

    require_within(cfg, src)
    require_within(cfg, dest.parent)

    if not src.exists():
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)

    if not dest.exists():
        shutil.move(str(src), str(dest))
        COUNT_MOVED += 1
        log(cfg, f'[MOVE] {src} -> {dest}')
        return dest

    try:
        for item in list(src.iterdir()):
            target = dest / item.name
            if target.exists():
                if item.is_dir() and target.is_dir():
                    merge_or_move_folder(item, target, cfg)
                if item.exists():
                    shutil.rmtree(item)
            else:
                shutil.move(str(item), str(target))

        if src.exists():
            shutil.rmtree(src)

        COUNT_MOVED += 1
        log(cfg, f'[MERGE OK] {src} -> {dest}')
        return dest

    except Exception as exc:
        fallback = resolve_merge_fallback_dir(dest)
        if src.exists():
            shutil.move(str(src), str(fallback))
        COUNT_ERRORS += 1
        log(cfg, f'[MOVE ALT] {src} -> {fallback} / reason={exc}', error=True)
        return fallback


def folder_hash(folder: Path) -> str:
    """Berechnet einen Hash für den JPG-Inhalt eines Ordners."""
    rows = []
    for p in sorted(folder.rglob('*')):
        if p.is_symlink() or not p.is_file() or p.suffix not in JPG_EXTS:
            continue
        rows.append(f'{p.relative_to(folder)}::{p.stat().st_size}')
    return hashlib.md5("\n".join(rows).encode('utf-8')).hexdigest()


def safe_delete(path: Path, cfg: dict) -> None:
    """Löscht eine Datei nur innerhalb des ARW-Verzeichnisses (98AP-Sicherheit)."""
    if cfg['safety'].get('never_delete_outside_arw_dir', True) and 'ARW' not in path.parts:
        raise ValueError(f'Refusing to delete outside ARW dir: {path}')

    require_within(cfg, path)

    if path.exists() and path.is_file():
        path.unlink()


def load_personal(cfg: dict):
    """Lädt oder rebuilt das persönliche Bewertungsmodell."""
    return load_or_rebuild_personal_model(cfg)


def score_image(path: Path, cfg: dict, model: dict | None) -> dict:
    """Berechnet alle Scores für ein Bild."""
    generic = generic_aesthetic_score(path)
    components = base_score_components(path, cfg)
    base_score = weighted_base_score(components, cfg)
    personal = personal_model_score(path, model)

    return {
        'generic_score': max(0.0, min(1.0, generic)),
        'base_score': max(0.0, min(1.0, base_score)),
        'personal_score': personal,
        'sharp_score': components.get('sharp'),
        'aesth_score': components.get('aesth'),
        'exposure_score': components.get('exposure'),
        'eye_score': components.get('eyes'),
        'reference_score': components.get('reference'),
    }


def combine_scores(base_score: float, eye_score: float | None, personal_score: float | None, family_score: float | None, cfg: dict) -> float:
    """Kombiniert alle Score-Komponenten zu einem Gesamtscore."""
    weights = cfg.get('culling', {}).get('component_weights', {})

    active = {
        'base_score': base_score,
        'eye_score': eye_score,
        'personal_score': personal_score,
        'family_score': family_score,
    }

    weighted = {
        key: float(weights.get(key, 0.0))
        for key, value in active.items()
        if value is not None and float(weights.get(key, 0.0)) > 0
    }

    total_weight = sum(weighted.values())

    if total_weight <= 0:
        return max(0.0, min(1.0, float(base_score)))

    score = sum(float(active[key]) * weighted[key] for key in weighted) / total_weight
    return max(0.0, min(1.0, float(score)))
    
def cull_folder(workdir: Path, cfg: dict) -> dict:
    """
    Führt das AI-Culling für einen Batch durch.
    
    98AP-Regeln:
      - AP2: MANUAL_KEEP hat Vorrang vor automatischer Bewertung
      - AP6: Face-Score nur bei ausreichender Referenzbasis
      - AP7: Nachvollziehbare Entscheidungen und Terminal-Ausgabe
      - AP8: MANUAL_KEEP inbox/used-Logik für idempotente Zuordnung
    """
    global LAST_FAMILY_RUN_INFO

    save_dir = ensure_dir(workdir / 'SAVE')
    rejected_dir = workdir / '_Rejected'
    review_dir = workdir / '_Review'

    if cfg['culling'].get('create_rejected_folder', True):
        rejected_dir.mkdir(exist_ok=True)
    if cfg['culling'].get('create_review_folder', True):
        review_dir.mkdir(exist_ok=True)

    # ==========================================================================
    # SCHRITT 1: Referenzprofile und Modelle laden
    # ==========================================================================
    reference_profile, reference_info = ensure_reference_profile(cfg)
    cfg.setdefault('culling', {}).setdefault('reference_scoring', {})['_runtime_profile'] = reference_profile

    log(cfg, f"[REFERENCE PROFILE] status={reference_info.get('status')} images={reference_info.get('reference_image_count', 0)} cache_used={reference_info.get('used_cache', False)} cache_rebuilt={reference_info.get('rebuilt_cache', False)} preview_size={reference_info.get('preview_size')}")

    personal_model, personal_info = load_personal(cfg)
    log(cfg, f"[PERSONAL MODEL] status={personal_info.get('status')} images={personal_info.get('source_image_count', 0)} cache_used={personal_info.get('used_cache', False)} cache_rebuilt={personal_info.get('rebuilt_cache', False)}")

    family_model = load_family_model(cfg)
    family_info = {
        'status': family_model.get('status'),
        'used_cache': family_model.get('used_cache', False),
        'rebuilt_cache': family_model.get('rebuilt_cache', False),
        'person_count': family_model.get('person_count', 0),
        'cache_dir': family_model.get('cache_dir'),
    }
    LAST_FAMILY_RUN_INFO = family_info
    log(cfg, f"[FAMILY MODEL] status={family_info['status']} people={family_info['person_count']} cache_used={family_info['used_cache']} cache_rebuilt={family_info['rebuilt_cache']}")

    # ==========================================================================
    # SCHRITT 2: MANUAL_KEEP prüfen (mit Feature-Vektor-Matching)
    # ==========================================================================
    manual_keep_inbox = Path(cfg['paths']['manual_keep_inbox'])
    manual_keep_used = Path(cfg['paths']['manual_keep_used'])

    manual_keep_cfg = cfg.get('manual_keep', {})
    similarity_threshold = float(manual_keep_cfg.get('similarity_threshold', 0.85))

    manual_keep_images, manual_keep_status = detect_manual_keep_images(
        batch_path=workdir,
        manual_keep_inbox=manual_keep_inbox,
        manual_keep_used=manual_keep_used,
        similarity_threshold=similarity_threshold,
    )

    # Terminal-Ausgabe für MANUAL_KEEP
    if manual_keep_status['status'] == 'matched':
        print(f"[MANUAL_KEEP] inbox={manual_keep_status['inbox_count']} matched={manual_keep_status['matched_count']} threshold={similarity_threshold}")
        for img in manual_keep_images:
            print(f"  [MANUAL_KEEP] KEEP: {img.name}")
    elif manual_keep_status['status'] == 'no_inbox':
        print(f"[MANUAL_KEEP] inbox-Ordner fehlt oder leer")
    elif manual_keep_status['status'] == 'empty_inbox':
        print(f"[MANUAL_KEEP] inbox-Ordner leer")
    elif manual_keep_status['status'] == 'no_match':
        print(f"[MANUAL_KEEP] keine ähnlichen Bilder gefunden (threshold={similarity_threshold})")

    # ==========================================================================
    # SCHRITT 3: Culling-Rows vorbereiten
    # ==========================================================================
    rows = []
    keep_threshold = float(cfg['culling']['keep_threshold'])
    reject_threshold = float(cfg['culling']['reject_threshold'])
    family_cfg = cfg.get('family_recognition', {})

    prediction = build_prediction_record(
        producer_version=SCRIPT_VERSION,
        batch_id=workdir.name,
        image_id=jpg.name,
        model_version=str(
            personal_info.get('model_version', 'personal-score-v1')
        ),
        predicted_decision='review',
        prediction_reason='manual_keep_override',
        personal_score=scored.get('personal_score'),
        final_score=1.0,
        predicted_at=datetime.now(timezone.utc).isoformat(),
    )

    for jpg in top_level_jpgs(workdir):
        # MANUAL_KEEP-Bilder zwingend als KEEP markieren (AP2)
        if jpg in manual_keep_images:
            scored = score_image(jpg, cfg, personal_model)
            family = detect_family_members(jpg, cfg, family_model)

            rows.append({
                '_source_path': jpg,
                '_family_tags': family.get('tags', []),
                '_family_regions': family.get('regions', []),
                'file': jpg.name,
                'generic_score': round(scored['generic_score'], 4),
                'base_score': round(scored['base_score'], 4),
                'sharp_score': '' if scored.get('sharp_score') is None else round(float(scored['sharp_score']), 4),
                'aesth_score': '' if scored.get('aesth_score') is None else round(float(scored['aesth_score']), 4),
                'exposure_score': '' if scored.get('exposure_score') is None else round(float(scored['exposure_score']), 4),
                'eye_score': '' if scored.get('eye_score') is None else round(float(scored['eye_score']), 4),
                'reference_score': '' if scored.get('reference_score') is None else round(float(scored['reference_score']), 4),
                'personal_score': '' if scored.get('personal_score') is None else round(float(scored['personal_score']), 4),
                'family_score': '' if family.get('family_score') is None else round(float(family.get('family_score')), 4),
                'final_score': 1.0,  # MANUAL_KEEP immer maximal
                'decision': 'keep',
                'decision_reason': 'manual_keep_match',
                'automation_mode': cfg['automation']['mode'],
                'predicted_decision': prediction['predicted_decision'],
                'prediction_reason': prediction['prediction_reason'],
                'prediction_model_version': prediction['model_version'],
                'predicted_at': prediction['predicted_at'],
                'prediction_schema_version': prediction['schema_version'],
                'prediction_producer_version': prediction['producer_version'],
                'protected_by_family_rule': False,
                'detected_people': '|'.join(family.get('detected_people', [])),
                'face_status': family.get('status', ''),
            })
            continue  # Weiteres Scrolling überspringen

        # Normales Scrolling für alle anderen Bilder
        scored = score_image(jpg, cfg, personal_model)
        family = detect_family_members(jpg, cfg, family_model)
        family_score = float(family.get('family_score', 0.0)) if family_cfg.get('enabled', False) else None
        final = combine_scores(scored['base_score'], scored.get('eye_score'), scored.get('personal_score'), family_score, cfg)

        predicted_decision, prediction_reason = predict_decision(
            personal_score=scored.get('personal_score'),
            final_score=final,
            config=cfg,
        )

        prediction = build_prediction_record(
            producer_version=SCRIPT_VERSION,
            batch_id=workdir.name,
            image_id=jpg.name,
            model_version=str(
                personal_info.get('model_version', 'personal-score-v1')
            ),
            predicted_decision=predicted_decision,
            prediction_reason=prediction_reason,
            personal_score=scored.get('personal_score'),
            final_score=final,
            predicted_at=datetime.now(timezone.utc).isoformat(),
        )

        decision = 'keep'
        score_reason = 'score_keep'
        protected = False

        if final < reject_threshold:
            if family.get('protected_by_family_rule', False):
                decision = 'review'
                score_reason = 'family_protected_score'
                protected = True
            else:
                decision = 'reject'
                score_reason = 'score_reject'
        elif final < keep_threshold:
            decision = 'review'
            score_reason = 'score_review'

        rows.append({
            '_source_path': jpg,
            '_family_tags': family.get('tags', []),
            '_family_regions': family.get('regions', []),
            'file': jpg.name,
            'generic_score': round(scored['generic_score'], 4),
            'base_score': round(scored['base_score'], 4),
            'sharp_score': '' if scored.get('sharp_score') is None else round(float(scored['sharp_score']), 4),
            'aesth_score': '' if scored.get('aesth_score') is None else round(float(scored['aesth_score']), 4),
            'exposure_score': '' if scored.get('exposure_score') is None else round(float(scored['exposure_score']), 4),
            'eye_score': '' if scored.get('eye_score') is None else round(float(scored['eye_score']), 4),
            'reference_score': '' if scored.get('reference_score') is None else round(float(scored['reference_score']), 4),
            'personal_score': '' if scored.get('personal_score') is None else round(float(scored['personal_score']), 4),
            'family_score': '' if family_score is None else round(float(family_score), 4),
            'final_score': round(final, 4),
            'decision': decision,
            'decision_reason': score_reason,
            'automation_mode': cfg['automation']['mode'],
            'predicted_decision': prediction['predicted_decision'],
            'prediction_reason': prediction['prediction_reason'],
            'prediction_model_version': prediction['model_version'],
            'predicted_at': prediction['predicted_at'],
            'prediction_schema_version': prediction['schema_version'],
            'prediction_producer_version': prediction['producer_version'],            
            'protected_by_family_rule': protected,
            'detected_people': '|'.join(family.get('detected_people', [])),
            'face_status': family.get('status', ''),
        })

    # ==========================================================================
    # SCHRITT 4: Series-Culling anwenden
    # ==========================================================================
    rows = apply_series_culling(rows, cfg)

    # MANUAL_KEEP hat Vorrang vor Series-Culling.
    for row in rows:
        if row.get('decision_reason') == 'manual_keep_match':
            row['decision'] = 'keep'
            row['decision_reason'] = 'manual_keep_match'
            row['final_score'] = 1.0

    family_tag_written = 0
    culling_metadata_written = 0

    # ==========================================================================
    # SCHRITT 5: Metadaten schreiben und Bilder verschieben
    # ==========================================================================
    for row in rows:
        jpg = row['_source_path']
        target_path = jpg

        if row['decision'] == 'reject' and cfg['culling'].get('move_files', True):
            target_path = rejected_dir / jpg.name
        elif row['decision'] == 'review' and cfg['culling'].get('move_files', True):
            target_path = review_dir / jpg.name

        if target_path != jpg:
            shutil.move(str(jpg), str(target_path))

        # Family-Tags schreiben (wenn aktiviert)
        family_metadata_ok, family_metadata_status = False, 'not_attempted'
        if family_cfg.get('enabled', False) and family_cfg.get('write_native_tags', True) and row.get('_family_tags'):
            family_metadata_ok, family_metadata_status = write_native_tags(
                target_path,
                row.get('_family_tags', []),
                cfg,
                row.get('_family_regions', []),
            )
            if family_metadata_ok:
                family_tag_written += 1

        # Culling-Metadaten schreiben
        culling_metadata_ok, culling_metadata_status = write_culling_metadata(target_path, row, cfg)
        if culling_metadata_ok:
            culling_metadata_written += 1

        # Row für CSV vorbereiten
        row['family_metadata_written'] = family_metadata_ok
        row['family_metadata_status'] = family_metadata_status
        row['culling_metadata_written'] = culling_metadata_ok
        row['culling_metadata_status'] = culling_metadata_status
        row['final_path'] = str(target_path.relative_to(workdir))
        row.pop('_source_path', None)
        row.pop('_family_tags', None)
        row.pop('_family_regions', None)

    # ==========================================================================
    # SCHRITT 6: CSV-Scores schreiben
    # ==========================================================================
    csv_path = save_dir / 'culling_scores.csv'
    fieldnames = [
        'file', 'generic_score', 'base_score', 'sharp_score', 'aesth_score', 'exposure_score',
        'eye_score', 'reference_score', 'personal_score', 'family_score', 'final_score',
        'score_decision', 'score_reason', 'decision', 'decision_reason',
        'automation_mode', 'predicted_decision', 'prediction_reason',
        'prediction_model_version', 'predicted_at', 'prediction_schema_version',
        'prediction_producer_version',        
        'series_id', 'series_size', 'series_rank', 'series_best', 'series_margin_to_best', 'star_rating',
        'protected_by_family_rule', 'detected_people', 'face_status', 'family_metadata_written',
        'family_metadata_status', 'culling_metadata_written', 'culling_metadata_status', 'final_path'
    ]

    with csv_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, '') for name in fieldnames})

    # ==========================================================================
    # SCHRITT 7: Summary erstellen
    # ==========================================================================
    clustered_rows = [r for r in rows if r.get('series_id') != 'single']
    summary = {
        'created_at': now(),
        'keep': sum(1 for r in rows if r['decision'] == 'keep'),
        'review': sum(1 for r in rows if r['decision'] == 'review'),
        'reject': sum(1 for r in rows if r['decision'] == 'reject'),
        'total': len(rows),
        'keep_threshold': keep_threshold,
        'reject_threshold': reject_threshold,
        'series_detection_enabled': bool(cfg.get('series_detection', {}).get('enabled', True)),
        'series_clustered_images': len(clustered_rows),
        'series_cluster_count': len({r['series_id'] for r in clustered_rows}),
        'series_best_images': sum(1 for r in rows if r.get('series_best')),
        'family_recognition_enabled': bool(family_cfg.get('enabled', False)),
        'family_tagged_images': sum(1 for r in rows if r['detected_people']),
        'family_protected_images': sum(1 for r in rows if r.get('protected_by_family_rule')),
        'family_cache_status': family_model.get('status'),
        'family_cache_used': family_model.get('used_cache', False),
        'family_cache_rebuilt': family_model.get('rebuilt_cache', False),
        'family_reference_people': family_model.get('person_count', 0),
        'family_metadata_written': family_tag_written,
        'culling_metadata_written': culling_metadata_written,
        # NEU: MANUAL_KEEP-Statistik
        'manual_keep_inbox_count': manual_keep_status.get('inbox_count', 0),
        'manual_keep_matched_count': manual_keep_status.get('matched_count', 0),
        'manual_keep_status': manual_keep_status.get('status', 'not_checked'),
    }

    (save_dir / 'culling_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')

    # ==========================================================================
    # SCHRITT 8: MANUAL_KEEP Quellen nach used/ verschieben (erst nach vollständigem Erfolg)
    # ==========================================================================
    if manual_keep_status['status'] == 'matched':
        move_result = move_manual_keep_sources_to_used(
            matched_source_paths=manual_keep_status['matched_source_paths'],
            manual_keep_inbox=manual_keep_inbox,
            manual_keep_used=manual_keep_used,
        )

        print(
            "[MANUAL_KEEP] "
            f"used_moved={move_result['moved_count']} "
            f"already_used={move_result['already_used_count']} "
            f"failed={move_result['failed_count']}"
        )

        for error in move_result['errors']:
            print(f"[MANUAL_KEEP] MOVE FAILED: {error}")

        summary['manual_keep_used_moved_count'] = move_result['moved_count']
        summary['manual_keep_used_failed_count'] = move_result['failed_count']

    return summary
    
def prepare_folder_phase1(folder: Path, cfg: dict) -> Path:
    """Bereitet einen Batch-Ordner für Phase 1 vor."""
    global COUNT_PROCESSED

    src_root = Path(cfg['paths']['temp_sd'])
    name = folder.name
    new_name = make_date_name(name, cfg)
    workdir = folder

    # Batch-Namen bei Bedarf korrigieren
    if name != new_name:
        workdir = src_root / new_name
        shutil.move(str(folder), str(workdir))
        log(cfg, f'[RENAMED] {name} -> {new_name}')

    # ARW-Dateien in Unterordner verschieben
    arw_dir = ensure_dir(workdir / 'ARW')
    for arw in top_level_arws(workdir):
        shutil.move(str(arw), str(arw_dir / arw.name))

    # ZIP-Archiv aller JPGs vor Culling erstellen
    save_dir = ensure_dir(workdir / 'SAVE')
    jpgs_before_cull = top_level_jpgs(workdir)
    zip_path = save_dir / f'{workdir.name}_ALL_JPG.zip'

    if jpgs_before_cull:
        create_zip(zip_path, jpgs_before_cull)
        log(cfg, f'[ZIP OK] {zip_path}')

    # Culling durchführen
    if cfg['culling'].get('enabled', True):
        summary = cull_folder(workdir, cfg)
        log(cfg, f"[CULL] keep={summary['keep']} review={summary['review']} reject={summary['reject']} total={summary['total']} family_tagged={summary['family_tagged_images']} family_cache_status={summary['family_cache_status']}")

    # Batch als abgeschlossen markieren
    (workdir / '.DONE').touch()
    COUNT_PROCESSED += 1
    log(cfg, f'[DONE] {workdir.name}')

    # Batch nach temp_images verschieben
    return merge_or_move_folder(workdir, Path(cfg['paths']['temp_images']) / workdir.name, cfg)


def run_phase1(cfg: dict, folder: str | None = None) -> None:
    """Führt Phase 1 (Culling) für alle Batches in temp_sd aus."""
    global COUNT_FOUND_SRC, COUNT_SKIPPED

    src_root = ensure_dir(cfg['paths']['temp_sd'])
    folders = [Path(folder)] if folder else [p for p in sorted(src_root.iterdir()) if p.is_dir()]

    for dir_path in folders:
        if not dir_path.exists() or not dir_path.is_dir():
            continue

        COUNT_FOUND_SRC += 1
        name = dir_path.name

        # Nur gültige Batch-Namen verarbeiten
        if not (is_valid_raw_folder(name) or is_valid_done_folder(name)):
            COUNT_SKIPPED += 1
            log(cfg, f'[SKIP TOP] Unsupported folder: {name}')
            continue

        # Stabilitätsprüfung
        if not (dir_path / '.DONE').exists() and not is_stable(dir_path, int(cfg['workflow']['wait_time_seconds'])):
            COUNT_SKIPPED += 1
            log(cfg, f'[WAIT] Transfer still running: {name}')
            continue

        # Bereits abgeschlossene Batches direkt verschieben
        if (dir_path / '.DONE').exists():
            merge_or_move_folder(dir_path, Path(cfg['paths']['temp_images']) / name, cfg)
            continue

        # Phase 1 ausführen
        prepare_folder_phase1(dir_path, cfg)


def process_done_folder(dir_path: Path, cfg: dict) -> None:
    """Verarbeitet einen abgeschlossenen Batch in temp_done (Phase 2)."""
    arw_dir = dir_path / 'ARW'
    save_dir = ensure_dir(dir_path / 'SAVE')

    if not arw_dir.exists():
        log(cfg, f'[SKIP DONE] No ARW directory: {dir_path.name}')
        return

    new_hash = folder_hash(dir_path)
    processed_marker = dir_path / '.PROCESSED'

    # Unveränderte Batches überspringen
    if processed_marker.exists() and processed_marker.read_text(encoding='utf-8').strip() == new_hash:
        log(cfg, f'[SKIP DONE] Folder unchanged: {dir_path.name}')
        return

    # ZIP-Artefakte bewahren
    for z in sorted(arw_dir.glob('*.zip')):
        preserve_zip_artifact(z, save_dir, dir_path.name, cfg)

    # ARWs ohne aktive JPGs löschen
    for arw in sorted(arw_dir.iterdir()):
        if not arw.is_file() or arw.suffix not in RAW_EXTS:
            continue
        base = arw.stem
        if not (dir_path / f'{base}.JPG').exists() and not (dir_path / f'{base}.jpg').exists():
            safe_delete(arw, cfg)
            log(cfg, f'[DELETE ARW] No matching active JPG: {base}')

    # Verbleibende ARWs archivieren
    remaining = [p for p in sorted(arw_dir.iterdir()) if p.is_file() and p.suffix in RAW_EXTS]
    zip_path = next_available_artifact_path(save_dir, dir_path.name, 'sort_arw')

    if remaining:
        create_zip(zip_path, remaining)

    shutil.rmtree(arw_dir)
    processed_marker.write_text(new_hash, encoding='utf-8')
    log(cfg, f'[DONE MARKED] {dir_path.name}')


def process_container_done(dir_path: Path, cfg: dict) -> None:
    """Verarbeitet einen Container-Ordner mit mehreren Batches."""
    for sub in sorted(dir_path.iterdir()):
        if sub.is_dir() and is_valid_done_folder(sub.name):
            process_done_folder(sub, cfg)


def run_phase2(cfg: dict, folder: str | None = None) -> None:
    """
    Führt Phase 2 (Archivierung + Cleanup) für alle Batches in temp_done aus.
    
    Reihenfolge:
      1. ARW-Zip erstellen (process_done_folder)
      2. State-Update (bereits in process_done_folder)
      3. Review/Rejected bereinigen (cleanup_review_rejected)
      4. Ordner löschen (_Review, _Rejected)
      5. Move nach temp_final (move_to_temp_final)
    """
    global COUNT_FOUND_DONE
    
    done_root = ensure_dir(cfg['paths']['temp_done'])
    folders = [Path(folder)] if folder else [p for p in sorted(done_root.iterdir()) if p.is_dir()]
    
    # Phase-2-Config auslesen
    phase2_cfg = cfg.get('phase2', {})
    cleanup_enabled = bool(phase2_cfg.get('cleanup_review_rejected', True))
    move_enabled = bool(phase2_cfg.get('move_to_temp_final', False))
    dry_run = bool(phase2_cfg.get('dry_run', False))
    
    for dir_path in folders:
        COUNT_FOUND_DONE += 1
        
        # Nur Ordner ohne führenden Punkt verarbeiten
        if dir_path.name.startswith('.'):
            continue
        
        if is_valid_done_folder(dir_path.name):
            # ==========================================================================
            # SCHRITT 1: Bestehende Phase-2-Archivierung (ARW-Zip, State-Update)
            # ==========================================================================
            process_done_folder(dir_path, cfg)
            
            # ==========================================================================
            # SCHRITT 2: Review/Rejected bereinigen (nur wenn aktiviert)
            # ==========================================================================
            if cleanup_enabled:
                from app.phase2_contract import cleanup_review_rejected, verify_cleanup_complete, move_to_temp_final
                
                cleanup_result = cleanup_review_rejected(
                    batch_path=str(dir_path),
                    cfg=cfg,
                    dry_run=dry_run,
                )
                
                log(cfg, f'[CLEANUP] {dir_path.name} keep={cleanup_result["review_keep_moved"]} reject={cleanup_result["review_reject_moved"]} rejected={cleanup_result["rejected_moved"]} status={cleanup_result["status"]}')
                
                if cleanup_result['errors']:
                    for error in cleanup_result['errors']:
                        log(cfg, f'[CLEANUP WARN] {dir_path.name} {error}', error=True)
                
                # ==========================================================================
                # SCHRITT 3: Bereinigung verifizieren
                # ==========================================================================
                verify_result = verify_cleanup_complete(str(dir_path))
                
                # Ordner wurden bereits gelöscht, verify_result zeigt nur den Status vor dem Löschen
                # Move nach temp_final nur wenn cleanup erfolgreich war
                if cleanup_result['status'] not in ['ok', 'partial']:
                    log(cfg, f'[PHASE2 FAILED] {dir_path.name} Cleanup fehlgeschlagen', error=True)
                    continue
                
                # ==========================================================================
                # SCHRITT 4: Move nach temp_final (nur wenn aktiviert + cleanup OK)
                # ==========================================================================
                if move_enabled:
                    move_result = move_to_temp_final(
                        batch_path=str(dir_path),
                        cfg=cfg,
                        dry_run=dry_run,
                    )
                    
                    if move_result['success']:
                        log(cfg, f'[PHASE2 OK] {dir_path.name} moved to temp_final')
                    elif move_result['error'] == 'move_to_temp_final ist in der Config deaktiviert':
                        log(cfg, f'[PHASE2 OK] {dir_path.name} move_to_temp_final deaktiviert')
                    else:
                        log(cfg, f'[PHASE2 FAILED] {dir_path.name} {move_result["error"]}', error=True)
                else:
                    log(cfg, f'[PHASE2 OK] {dir_path.name} cleanup abgeschlossen, move deaktiviert')
            else:
                log(cfg, f'[PHASE2 OK] {dir_path.name} cleanup deaktiviert')
        else:
            process_container_done(dir_path, cfg)

def run_training(cfg: dict, images_dir: str | None = None, model_out: str | None = None) -> None:
    """Trainiert das persönliche Bewertungsmodell."""
    images_dir = images_dir or cfg['training']['sample_images_dir']
    model_out = model_out or cfg['paths']['personal_model']
    labels_out = str(Path(cfg['training']['exported_labels_dir']) / 'training_labels.csv')

    model = train_from_directory(
        images_dir=images_dir,
        model_out=model_out,
        labels_out=labels_out,
        min_images=int(cfg['training'].get('min_labeled_images', 20)),
    )

    log(cfg, f"[TRAIN] model={model_out} rows={model['training_rows']}")

def run_family_cache_rebuild(cfg: dict) -> None:
    """Baut den Family-Cache komplett neu auf."""
    global LAST_FAMILY_RUN_INFO

    report = rebuild_family_cache(cfg)
    LAST_FAMILY_RUN_INFO = report

    log(cfg, f"[FAMILY CACHE] status={report['status']} people={report['person_count']} rebuilt={report['rebuilt_cache']} cache_dir={report['cache_dir']}")


def build_parser() -> argparse.ArgumentParser:
    """Erstellt den CLI-Parser für alle Commands."""
    parser = argparse.ArgumentParser(description='Synology photo workflow with AI-assisted culling.')
    parser.add_argument('--config', default='config/config.yaml')
    
    sub = parser.add_subparsers(dest='command', required=True)
    
    # Phase 1
    p1 = sub.add_parser('phase1')
    p1.add_argument('--folder', default=None)
    
    # Phase 2
    p2 = sub.add_parser('phase2')
    p2.add_argument('--folder', default=None)
    
    # Pipeline (konfigurierbar)
    p_pipe = sub.add_parser('pipeline')
    p_pipe.add_argument('--folder', default=None)
    
    # Alias: phase12 (identisch zu pipeline)
    p12 = sub.add_parser('phase12')
    p12.add_argument('--folder', default=None)
    
    # Training
    train = sub.add_parser('train-personal')
    train.add_argument('--images-dir', default=None)
    train.add_argument('--model-out', default=None)
    
    # Family Cache Rebuild
    sub.add_parser('rebuild-family-cache')
    
    return parser
    

def main() -> int:
    """Haupt-Entry-Point für den Workflow."""
    global COUNT_ERRORS

    reset_counters()
    parser = build_parser()
    args = parser.parse_args()
    cfg = load_config(args.config)
    started_at = now()

    print_start_banner(cfg, args.command)

    # Verzeichnisse sicherstellen
    for key in ['temp_sd', 'temp_images', 'temp_done']:
        ensure_dir(cfg['paths'][key])
    ensure_dir(Path(cfg['paths']['personal_model']).parent)
    ensure_dir(cfg['family_recognition']['cache_dir'])

    status = 'success'

    try:
        with file_lock(cfg):
            if args.command == 'phase1':
                run_phase1(cfg, args.folder)
            elif args.command == 'phase2':
                run_phase2(cfg, args.folder)
            elif args.command in ('pipeline', 'phase12'):
                run_pipeline(cfg, args.folder)
            elif args.command == 'train-personal':
                run_training(cfg, args.images_dir, args.model_out)
            elif args.command == 'rebuild-family-cache':
                run_family_cache_rebuild(cfg)

    except Exception as exc:
        COUNT_ERRORS += 1
        status = 'error'
        log(cfg, f'[FATAL] {exc}', error=True)

    finally:
        finished_at = now()
        payload = build_summary_payload(cfg, args.command, status, started_at, finished_at, None)
        summary_path = write_json_summary(cfg, payload)
        payload = build_summary_payload(cfg, args.command, status, started_at, finished_at, summary_path)
        print_scheduler_summary(cfg, payload)

    return 0 if status == 'success' else 1


if __name__ == '__main__':
    raise SystemExit(main())