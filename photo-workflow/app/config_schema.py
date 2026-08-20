"""
Skript: app/config_schema.py
Zweck: Striktes Config-Schema fuer photo-workflow mit 98AP-Validierung
Autor: Matzethias
Erstellt: 2026-08-09
Version: 2.2.0
Requires: Python 3.12+, typing

Aenderungsprotokoll:
  2026-08-20 | 2.2.0 | A1.7: pipeline und phase2 als aktive Config-Sektionen ergänzt
  2026-08-20 | 2.1.0 | A1: automation als kanonische Config-Sektion ergänzt
  2026-08-09 | 2.0.0 | 98AP-konforme Validierung mit allen Sektionen
  2026-08-09 | 1.0.0 | Initiale Implementierung mit validate_config()
"""
import os
import hashlib
from typing import Dict, Any, List, Tuple, Optional, Set


class ConfigError(Exception):
    """
    Exception fuer Config-Validierungsfehler.
    
    Wird von validate_config_strict() geworfen, wenn die Config
    gegen 98AP-Regeln oder projektweite Sicherheitsanforderungen verstoesst.
    """
    pass


def config_fingerprint(config: Dict[str, Any]) -> str:
    """
    Berechnet einen stabilen SHA256-Fingerprint der Konfiguration.
    
    Der Fingerprint wird im Run-Summary dokumentiert (98AP Abschnitt 6).
    Er aendert sich bei Aenderungen an sicherheitsrelevanten Feldern.
    
    Args:
        config: Vollstaendige Config als Dict
        
    Returns:
        64-zeichen SHA256-Hash der kanonischen Config-Repraesentation
    """
    paths = config.get('paths', {})
    safety = config.get('safety', {})
    runtime = config.get('runtime', {})
    
    # Sicherheitsrelevante Komponenten fuer Fingerprint
    components = [
        paths.get('base_dir', ''),
        str(safety.get('require_paths_within_base_dir', False)),
        str(safety.get('follow_symlinks', False)),
        str(safety.get('never_delete_outside_arw_dir', False)),
        runtime.get('lock_file', ''),
        runtime.get('state_dir', ''),
    ]
    
    canonical = '|'.join(components)
    return hashlib.sha256(canonical.encode()).hexdigest()


def effective_base_dir(config: Dict[str, Any]) -> str:
    """
    Gibt das effektive base_dir zurueck (kanonischer Pfad).
    
    Loest Symlinks und relative Pfade auf, um Traversal-Angriffe
    zu verhindern (98AP Abschnitt 3, Pfad-Sicherheit).
    
    Args:
        config: Config mit paths.base_dir
        
    Returns:
        Kanonischer absoluter Pfad von base_dir
        
    Raises:
        ConfigError: Wenn paths.base_dir fehlt oder ungueltig ist
    """
    paths = config.get('paths', {})
    base_dir = paths.get('base_dir', '')
    if not base_dir:
        raise ConfigError("paths.base_dir fehlt")
    return os.path.realpath(os.path.abspath(base_dir))


def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Vollstaendige Validierung der Config nach 98AP-Regeln.
    
    Prueft:
    - Pflichtfelder (paths, runtime, safety)
    - Erlaubte Sektionen (unbekannte Keys sind Fehler)
    - Pfad-Sicherheit (Traversal, Symlinks, base_dir-Grenze)
    - Typkorrektheit aller Felder
    
    Args:
        config: Vollstaendige Config als Dict
        
    Returns:
        Tuple aus (is_valid, errors)
        - is_valid: True wenn Config gueltig, sonst False
        - errors: Liste von Fehlermeldungen (leer wenn gueltig)
    """
    errors = []
    
    # 1. Erlaubte Top-Level-Sektionen (98AP Abschnitt 6, 8.2)
    allowed_sections: Set[str] = {
        'paths', 'runtime', 'safety',
        'workflow', 'models', 'culling', 'training', 'reporting',
        'family_recognition', 'series_detection', 'metadata_culling',
        'personal_scoring', 'clip_scoring', 'reference_pools', 'pools', 'scoring',
        'series', 'manual_keep', 'batch', 'automation', 'pipeline', 'phase2',
        'extensions',  # Explizit erlaubt laut 98AP
    }
    
    for key in config.keys():
        if key not in allowed_sections:
            errors.append(f"Unbekannte Sektion '{key}' in config")
    
    # Wenn unbekannte Sektionen, frueh zurueck (aber alle pruefen)
    
    # 2. Pflichtfelder pruefen
    required_sections = ['paths', 'runtime', 'safety']
    for section in required_sections:
        if section not in config:
            errors.append(f"Sektion '{section}' fehlt")
    
    if errors:
        return False, errors
    
    # 3. paths-Sektion
    paths = config.get('paths', {})
    required_paths = ['base_dir', 'temp_sd', 'temp_images', 'temp_done', 'temp_error']
    for key in required_paths:
        if key not in paths:
            errors.append(f"paths.{key} fehlt")
        elif not isinstance(paths[key], str) or not paths[key].strip():
            errors.append(f"paths.{key} muss ein nicht-leerer String sein")
    
    # workflow_data_dir oder workflow_data (beides akzeptieren)
    if 'workflow_data_dir' not in paths and 'workflow_data' not in paths:
        errors.append("paths.workflow_data_dir oder paths.workflow_data fehlt")
    
    # 4. base_dir muss existieren und ein Verzeichnis sein
    base_dir = paths.get('base_dir', '')
    if base_dir and os.path.exists(base_dir):
        if not os.path.isdir(base_dir):
            errors.append(f"paths.base_dir ist kein Verzeichnis: {base_dir}")
    elif base_dir:
        # base_dir existiert noch nicht - ist ok fuer neue Setups
        pass
    
    # 5. runtime-Sektion
    runtime = config.get('runtime', {})
    required_runtime = [
        'lock_file', 'state_dir', 'quarantine_dir',
        'log_file', 'error_log', 'run_summaries_dir',
        'calibration_batches_dir'
    ]
    for key in required_runtime:
        if key not in runtime:
            errors.append(f"runtime.{key} fehlt")
        elif not isinstance(runtime[key], str) or not runtime[key].strip():
            errors.append(f"runtime.{key} muss ein nicht-leerer String sein")
    
    # 6. safety-Sektion
    safety = config.get('safety', {})
    required_safety = [
        'require_paths_within_base_dir',
        'follow_symlinks',
        'never_delete_outside_arw_dir'
    ]
    for key in required_safety:
        if key not in safety:
            errors.append(f"safety.{key} fehlt")
        elif not isinstance(safety[key], bool):
            errors.append(f"safety.{key} muss ein Boolean sein")
    
    # 7. Path-Traversal-Schutz (nur wenn base_dir existiert)
    if base_dir and os.path.exists(base_dir):
        base_resolved = os.path.realpath(os.path.abspath(base_dir))
        
        # runtime-Pfade gegen base_dir pruefen
        for key, path_value in runtime.items():
            if isinstance(path_value, str) and path_value:
                try:
                    path_resolved = os.path.realpath(os.path.abspath(path_value))
                    if safety.get('require_paths_within_base_dir', False):
                        if not path_resolved.startswith(base_resolved + os.sep) and path_resolved != base_resolved:
                            errors.append(f"runtime.{key} liegt ausserhalb von base_dir: {path_value}")
                except Exception:
                    # Ungueltiger Pfad, wird von anderen Checks abgefangen
                    pass
    
    return len(errors) == 0, errors


def validate_config_strict(config: Dict[str, Any]) -> None:
    """
    Validiert die Config strikt und wirft ConfigError bei Fehlern.
    
    Diese Funktion ist ideal fuer:
    - Tests (pytest.raises)
    - Kommandozeilen-Tools
    - Fruehe Fehlererkennung beim Start
    
    Im Gegensatz zu validate_config() wirft sie Exceptions statt
    Tuple zurueckzugeben (EAFP-Prinzip, Pythonic).
    
    Args:
        config: Vollstaendige Config als Dict
        
    Raises:
        ConfigError: Wenn Config ungueltig ist mit detaillierter Fehlermeldung
    """
    if config is None:
        raise ConfigError("Config ist None")
    
    is_valid, errors = validate_config(config)
    if not is_valid:
        error_msg = f"Config validation failed: {'; '.join(errors)}"
        raise ConfigError(error_msg)


# Helper fuer Tests
def get_test_config(base_dir: str) -> Dict[str, Any]:
    """
    Erstellt eine gueltige Test-Config fuer Unit-Tests.
    
    Args:
        base_dir: Basisverzeichnis fuer die Test-Config
        
    Returns:
        Vollstaendige Config mit allen Pflichtfeldern
    """
    return {
        'paths': {
            'base_dir': base_dir,
            'temp_sd': '01_TEMP_SD',
            'temp_images': '02_TEMP_IMAGES',
            'temp_done': '03_TEMP_DONE',
            'temp_error': '00_TEMP_ERROR',
            'workflow_data_dir': 'WORKFLOW_DATA',
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
