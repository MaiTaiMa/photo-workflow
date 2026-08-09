"""
# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/runtime_paths.py
# PURPOSE:     Validierung und Erzeugung von Runtime-Pfaden fuer AP2
# AUTHOR:      Benjamin (via AP2-Implementierung)
# DATE:        2026-08-09
# VERSION:     1.0.0 (AP2)
# REQUIRES:    Python 3.8+, config.yaml mit runtime-Sektion
# CHANGES:
#   2026-08-09: Initiale Implementierung fuer AP2
# =============================================================================
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple, Any

REQUIRED_RUNTIME_KEYS = [
    'lock_file', 'state_dir', 'quarantine_dir', 'log_file', 'error_log',
    'run_summaries_dir', 'calibration_batches_dir',
]

def is_path_within_base(path: str, base_dir: str) -> bool:
    if '..' in path:
        return False
    base_resolved = os.path.realpath(os.path.abspath(base_dir))
    path_resolved = os.path.realpath(os.path.abspath(path))
    return path_resolved.startswith(base_resolved + os.sep) or path_resolved == base_resolved

def validate_path_safe(path: str, base_dir: str, allow_symlinks: bool = False) -> Tuple[bool, List[str]]:
    errors = []
    if '..' in path:
        errors.append(f"Path-Traversal erkannt: {path}")
        return False, errors
    if not path or not path.strip():
        errors.append("Pfad ist leer")
        return False, errors
    if not is_path_within_base(path, base_dir):
        errors.append(f"Pfad liegt ausserhalb von base_dir: {path}")
        return False, errors
    return True, errors

def validate_runtime_paths(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors = []
    paths_config = config.get('paths', {})
    base_dir = paths_config.get('base_dir')
    if not base_dir:
        errors.append("paths.base_dir fehlt oder ist leer")
        return False, errors
    if not os.path.isdir(base_dir):
        errors.append(f"paths.base_dir existiert nicht: {base_dir}")
        return False, errors
    runtime_config = config.get('runtime', {})
    if not runtime_config:
        errors.append("runtime-Sektion fehlt in der Config")
        return False, errors
    for key in REQUIRED_RUNTIME_KEYS:
        if key not in runtime_config:
            errors.append(f"runtime.{key} fehlt")
        else:
            path_value = runtime_config[key]
            if not isinstance(path_value, str):
                errors.append(f"runtime.{key} muss ein String sein")
                continue
            if not path_value.strip():
                errors.append(f"runtime.{key} ist leer")
                continue
            is_valid, path_errors = validate_path_safe(path_value, base_dir, allow_symlinks=False)
            if not is_valid:
                errors.extend([f"runtime.{key}: {err}" for err in path_errors])
    return len(errors) == 0, errors

def create_runtime_dirs(config: Dict[str, Any], dry_run: bool = False) -> Tuple[bool, List[str], List[str]]:
    created_dirs = []
    errors = []
    paths_config = config.get('paths', {})
    runtime_config = config.get('runtime', {})
    base_dir = paths_config.get('base_dir')
    if not base_dir:
        errors.append("paths.base_dir nicht vorhanden")
        return False, created_dirs, errors
    dir_keys = ['state_dir', 'quarantine_dir', 'run_summaries_dir', 'calibration_batches_dir']
    for key in dir_keys:
        if key in runtime_config:
            dir_path = runtime_config[key]
            if not dry_run:
                try:
                    os.makedirs(dir_path, exist_ok=True)
                    created_dirs.append(dir_path)
                except OSError as e:
                    errors.append(f"Fehler beim Erstellen von {dir_path}: {e}")
            else:
                created_dirs.append(f"(dry-run) {dir_path}")
    if 'lock_file' in runtime_config:
        lock_dir = os.path.dirname(runtime_config['lock_file'])
        if not dry_run:
            try:
                os.makedirs(lock_dir, exist_ok=True)
                created_dirs.append(lock_dir)
            except OSError as e:
                errors.append(f"Fehler beim Erstellen von {lock_dir}: {e}")
        else:
            created_dirs.append(f"(dry-run) {lock_dir}")
    if 'log_file' in runtime_config:
        log_dir = os.path.dirname(runtime_config['log_file'])
        if not dry_run:
            try:
                os.makedirs(log_dir, exist_ok=True)
                if log_dir not in created_dirs:
                    created_dirs.append(log_dir)
            except OSError as e:
                errors.append(f"Fehler beim Erstellen von {log_dir}: {e}")
    return len(errors) == 0, created_dirs, errors

def initialize_runtime(config: Dict[str, Any], dry_run: bool = False) -> Tuple[bool, Dict[str, Any]]:
    result = {'valid': False, 'errors': [], 'created_dirs': [], 'runtime_paths': {}}
    is_valid, errors = validate_runtime_paths(config)
    result['valid'] = is_valid
    result['errors'] = errors
    if not is_valid:
        return False, result
    if not dry_run:
        success, created_dirs, dir_errors = create_runtime_dirs(config, dry_run=False)
        result['created_dirs'] = created_dirs
        result['errors'].extend(dir_errors)
        if not success:
            return False, result
    runtime_config = config.get('runtime', {})
    result['runtime_paths'] = {
        'lock_file': runtime_config.get('lock_file'),
        'state_dir': runtime_config.get('state_dir'),
        'quarantine_dir': runtime_config.get('quarantine_dir'),
        'log_file': runtime_config.get('log_file'),
        'error_log': runtime_config.get('error_log'),
        'run_summaries_dir': runtime_config.get('run_summaries_dir'),
        'calibration_batches_dir': runtime_config.get('calibration_batches_dir'),
    }
    return True, result

def get_test_config(base_dir: str) -> Dict[str, Any]:
    return {
        'paths': {
            'base_dir': base_dir,
            'temp_sd': '01_TEMP_SD',
            'temp_images': '02_TEMP_IMAGES',
            'temp_done': '03_TEMP_DONE',
            'temp_error': '00_TEMP_ERROR',
            'workflow_data': 'WORKFLOW_DATA',
        },
        'runtime': {
            'lock_file': os.path.join(base_dir, 'WORKFLOW_DATA', 'runtime', 'locks', '.script.lock'),
            'state_dir': os.path.join(base_dir, 'WORKFLOW_DATA', 'runtime', 'state'),
            'quarantine_dir': os.path.join(base_dir, 'WORKFLOW_DATA', 'runtime', 'quarantine'),
            'log_file': os.path.join(base_dir, 'WORKFLOW_DATA', 'runtime', 'logs', 'process.log'),
            'error_log': os.path.join(base_dir, 'WORKFLOW_DATA', 'runtime', 'logs', 'error.log'),
            'run_summaries_dir': os.path.join(base_dir, 'WORKFLOW_DATA', 'runtime', 'run_summaries'),
            'calibration_batches_dir': os.path.join(base_dir, 'WORKFLOW_DATA', 'runtime', 'calibration', 'batches'),
        },
        'safety': {
            'require_paths_within_base_dir': True,
            'follow_symlinks': False,
            'never_delete_outside_arw_dir': True,
        },
    }
