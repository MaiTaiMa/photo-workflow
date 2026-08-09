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
import hashlib
from typing import Dict, Any, List, Tuple, Optional

class ConfigError(Exception):
    """Exception fuer Config-Validierungsfehler"""
    pass

def config_fingerprint(config: Dict[str, Any]) -> str:
    """
    Berechnet einen stabilen Fingerprint der Config.
    Aenderungen an sicherheitsrelevanten Feldern aendern den Fingerprint.
    """
    paths = config.get('paths', {})
    safety = config.get('safety', {})
    runtime = config.get('runtime', {})
    
    components = [
        paths.get('base_dir', ''),
        str(safety.get('require_paths_within_base_dir', False)),
        str(safety.get('follow_symlinks', False)),
        str(safety.get('never_delete_outside_arw_dir', False)),
        runtime.get('lock_file', ''),
        runtime.get('state_dir', ''),
    ]
    
    canonical = '|'.join(components)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]

def effective_base_dir(config: Dict[str, Any]) -> str:
    """
    Gibt das effektive base_dir zurueck (kanonischer Pfad).
    """
    paths = config.get('paths', {})
    base_dir = paths.get('base_dir', '')
    if not base_dir:
        raise ConfigError("paths.base_dir fehlt")
    return os.path.realpath(os.path.abspath(base_dir))

def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Vollstaendige Validierung der Config.
    Returns: (is_valid, errors)
    """
    errors = []
    
    # 1. Pflichtfelder pruefen
    required_sections = ['paths', 'runtime', 'safety']
    for section in required_sections:
        if section not in config:
            errors.append(f"Sektion '{section}' fehlt")
    
    if errors:
        return False, errors
    
    # 2. paths-Sektion
    paths = config.get('paths', {})
    required_paths = ['base_dir', 'temp_sd', 'temp_images', 'temp_done', 'temp_error', 'workflow_data']
    for key in required_paths:
        if key not in paths:
            errors.append(f"paths.{key} fehlt")
        elif not isinstance(paths[key], str) or not paths[key].strip():
            errors.append(f"paths.{key} muss ein nicht-leerer String sein")
    
    # 3. base_dir muss existieren
    base_dir = paths.get('base_dir', '')
    if base_dir and os.path.exists(base_dir):
        if not os.path.isdir(base_dir):
            errors.append(f"paths.base_dir ist kein Verzeichnis: {base_dir}")
    elif base_dir:
        # base_dir existiert noch nicht - ist ok fuer neue Setups
        pass
    
    # 4. runtime-Sektion
    runtime = config.get('runtime', {})
    required_runtime = ['lock_file', 'state_dir', 'quarantine_dir', 'log_file', 'error_log', 'run_summaries_dir', 'calibration_batches_dir']
    for key in required_runtime:
        if key not in runtime:
            errors.append(f"runtime.{key} fehlt")
        elif not isinstance(runtime[key], str) or not runtime[key].strip():
            errors.append(f"runtime.{key} muss ein nicht-leerer String sein")
    
    # 5. safety-Sektion
    safety = config.get('safety', {})
    required_safety = ['require_paths_within_base_dir', 'follow_symlinks', 'never_delete_outside_arw_dir']
    for key in required_safety:
        if key not in safety:
            errors.append(f"safety.{key} fehlt")
        elif not isinstance(safety[key], bool):
            errors.append(f"safety.{key} muss ein Boolean sein")
    
    # 6. Path-Traversal-Schutz (wenn base_dir existiert)
    if base_dir and os.path.exists(base_dir):
        base_resolved = os.path.realpath(os.path.abspath(base_dir))
        for key, path_value in runtime.items():
            if isinstance(path_value, str) and path_value:
                try:
                    path_resolved = os.path.realpath(os.path.abspath(path_value))
                    if safety.get('require_paths_within_base_dir', False):
                        if not path_resolved.startswith(base_resolved + os.sep) and path_resolved != base_resolved:
                            errors.append(f"runtime.{key} liegt ausserhalb von base_dir: {path_value}")
                except:
                    pass
    
    return len(errors) == 0, errors

# Helper fuer Tests
def get_test_config(base_dir: str) -> Dict[str, Any]:
    """Erstellt eine gueltige Test-Config"""
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

def validate_config_strict(config: Dict[str, Any]) -> None:
    """
    Validiert die Config strikt.
    Wirft ConfigError bei ungueltiger Config.
    
    Ideal fuer:
    - Tests (pytest.raises)
    - Kommandozeilen-Tools
    - Fruehe Fehlererkennung
    
    Abwaertskompatibilitaet:
    - validate_config() bleibt unveraendert (gibt Tuple zurueck)
    - Bestehender Code wird nicht beeinflusst
    """
    is_valid, errors = validate_config(config)
    if not is_valid:
        error_msg = f"Config validation failed: {'; '.join(errors)}"
        raise ConfigError(error_msg)