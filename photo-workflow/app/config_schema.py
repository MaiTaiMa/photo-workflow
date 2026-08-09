"""
# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/config_schema.py
# PURPOSE:     Striktes Schema für Pflichtfelder der Config (AP2)
# AUTHOR:      Benjamin (via AP2-Implementierung)
# DATE:        2026-08-09
# VERSION:     1.0.0 (AP2)
# REQUIRES:    Python 3.8+, PyYAML
# CHANGES:
#   2026-08-09: Initiale Implementierung für AP2
# =============================================================================
"""

import os
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

REQUIRED_TOP_LEVEL_KEYS = ['paths', 'workflow', 'safety']
OPTIONAL_TOP_LEVEL_KEYS = ['runtime', 'scoring', 'faces', 'models', 'culling', 'personal_training']

class ConfigSchema:
    """Striktes Schema für die Config-Validierung."""
    
    def __init__(self, strict: bool = True):
        self.strict = strict
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """Validiert die gesamte Config."""
        self.errors = []
        self.warnings = []
        self._validate_top_level(config)
        if 'paths' in config:
            self._validate_paths(config['paths'])
        if 'workflow' in config:
            self._validate_workflow(config['workflow'])
        if 'safety' in config:
            self._validate_safety(config['safety'])
        if 'runtime' in config:
            self._validate_runtime(config['runtime'], config.get('paths', {}).get('base_dir', ''))
        for section in ['scoring', 'faces', 'models', 'culling', 'personal_training']:
            if section in config:
                self._validate_section(section, config[section])
        return len(self.errors) == 0, self.errors, self.warnings
    
    def _validate_top_level(self, config: Dict[str, Any]) -> None:
        for key in REQUIRED_TOP_LEVEL_KEYS:
            if key not in config:
                self.errors.append(f"Erforderliche Sektion '{key}' fehlt")
        if self.strict:
            for key in config.keys():
                if key not in REQUIRED_TOP_LEVEL_KEYS + OPTIONAL_TOP_LEVEL_KEYS:
                    self.warnings.append(f"Unbekannte Top-Level-Sektion: '{key}'")
    
    def _validate_paths(self, paths: Dict[str, Any]) -> None:
        required_paths = ['base_dir', 'temp_sd', 'temp_images', 'temp_done', 'temp_error']
        for key in required_paths:
            if key not in paths:
                self.errors.append(f"paths.{key} fehlt (Pflichtfeld)")
            elif not isinstance(paths[key], str) or not paths[key].strip():
                self.errors.append(f"paths.{key} muss ein nicht-leerer String sein")
        optional_paths = ['temp_final', 'manual_keep_inbox', 'manual_keep_used', 'workflow_data']
        for key in optional_paths:
            if key in paths:
                if not isinstance(paths[key], str):
                    self.errors.append(f"paths.{key} muss ein String sein")
    
    def _validate_workflow(self, workflow: Dict[str, Any]) -> None:
        if 'wait_time_seconds' in workflow:
            if not isinstance(workflow['wait_time_seconds'], int):
                self.errors.append("workflow.wait_time_seconds muss eine Ganzzahl sein")
            elif workflow['wait_time_seconds'] < 0:
                self.errors.append("workflow.wait_time_seconds muss >= 0 sein")
        if 'stale_lock_seconds' in workflow:
            if not isinstance(workflow['stale_lock_seconds'], int):
                self.errors.append("workflow.stale_lock_seconds muss eine Ganzzahl sein")
            elif workflow['stale_lock_seconds'] <= 0:
                self.errors.append("workflow.stale_lock_seconds muss > 0 sein")
        if 'create_done_marker_before_move' in workflow:
            if not isinstance(workflow['create_done_marker_before_move'], bool):
                self.errors.append("workflow.create_done_marker_before_move muss ein Boolean sein")
    
    def _validate_safety(self, safety: Dict[str, Any]) -> None:
        if 'require_paths_within_base_dir' in safety:
            if not isinstance(safety['require_paths_within_base_dir'], bool):
                self.errors.append("safety.require_paths_within_base_dir muss ein Boolean sein")
        if 'follow_symlinks' in safety:
            if not isinstance(safety['follow_symlinks'], bool):
                self.errors.append("safety.follow_symlinks muss ein Boolean sein")
        if 'never_delete_outside_arw_dir' in safety:
            if not isinstance(safety['never_delete_outside_arw_dir'], bool):
                self.errors.append("safety.never_delete_outside_arw_dir muss ein Boolean sein")
    
    def _validate_runtime(self, runtime: Dict[str, Any], base_dir: str) -> None:
        required_runtime = ['lock_file', 'state_dir', 'quarantine_dir', 'log_file', 'error_log', 'run_summaries_dir', 'calibration_batches_dir']
        for key in required_runtime:
            if key not in runtime:
                self.errors.append(f"runtime.{key} fehlt (Pflichtfeld für AP2)")
            elif not isinstance(runtime[key], str) or not runtime[key].strip():
                self.errors.append(f"runtime.{key} muss ein nicht-leerer String sein")
            elif base_dir:
                if '..' in runtime[key]:
                    self.errors.append(f"runtime.{key} enthält Path-Traversal (..)")
                elif not runtime[key].startswith(base_dir):
                    self.errors.append(f"runtime.{key} liegt außerhalb von base_dir ({base_dir})")
    
    def _validate_section(self, section_name: str, section: Dict[str, Any]) -> None:
        if not isinstance(section, dict):
            self.errors.append(f"{section_name} muss ein Dictionary sein")
        elif not section:
            self.warnings.append(f"{section_name} ist leer")

def load_and_validate_config(config: Dict[str, Any], strict: bool = True) -> Tuple[bool, Dict[str, Any]]:
    """Lade und validiere Config (nach YAML-Laden)."""
    schema = ConfigSchema(strict=strict)
    is_valid, errors, warnings = schema.validate(config)
    result = {'valid': is_valid, 'errors': errors, 'warnings': warnings, 'config': config if is_valid else {}}
    return is_valid, result

def get_config_template() -> Dict[str, Any]:
    """Gibt eine Vorlage für eine gültige Config zurück."""
    return {
        'paths': {
            'base_dir': '/path/to/base',
            'temp_sd': '01_TEMP_SD',
            'temp_images': '02_TEMP_IMAGES',
            'temp_done': '03_TEMP_DONE',
            'temp_error': '00_TEMP_ERROR',
            'temp_final': '04_TEMP_FINAL',
            'manual_keep_inbox': 'MANUAL_KEEP/inbox',
            'manual_keep_used': 'MANUAL_KEEP/used',
            'workflow_data': 'WORKFLOW_DATA',
        },
        'workflow': {
            'wait_time_seconds': 60,
            'stale_lock_seconds': 43200,
            'create_done_marker_before_move': True,
        },
        'safety': {
            'require_paths_within_base_dir': True,
            'follow_symlinks': False,
            'never_delete_outside_arw_dir': True,
        },
        'runtime': {
            'lock_file': '/path/to/base/WORKFLOW_DATA/runtime/locks/.script.lock',
            'state_dir': '/path/to/base/WORKFLOW_DATA/runtime/state',
            'quarantine_dir': '/path/to/base/WORKFLOW_DATA/runtime/quarantine',
            'log_file': '/path/to/base/WORKFLOW_DATA/runtime/logs/process.log',
            'error_log': '/path/to/base/WORKFLOW_DATA/runtime/logs/error.log',
            'run_summaries_dir': '/path/to/base/WORKFLOW_DATA/runtime/run_summaries',
            'calibration_batches_dir': '/path/to/base/WORKFLOW_DATA/runtime/calibration/batches',
        },
    }