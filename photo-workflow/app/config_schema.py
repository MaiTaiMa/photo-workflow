"""
Skript: app/config_schema.py
Zweck: Lädt, validiert und fingerprintet die Workflow-Konfiguration.
Autor: MaiTaiMa
Erstellt: 2026-08-08
Version: 1.1
Requires: Python 3.11, PyYAML

Änderungsprotokoll:
  2026-08-08 | 1.1 | AP22.1 Header, Kommentare und Formatierung ergänzt
"""

from __future__ import annotations

# === Standardbibliothek ===
# Zweck: Stellt Hashing, JSON-Kanonisierung und Pfadverarbeitung bereit.
# Eingabe: Konfigurationsobjekte oder YAML-Dateien.
# Ausgabe: Validierte Werte und reproduzierbare Fingerprints.
import hashlib
import json
from pathlib import Path
from typing import Any

# === Externe Abhängigkeiten ===
# Zweck: Liest die zentrale YAML-Konfiguration.
# Voraussetzung: PyYAML muss in der Laufzeitumgebung installiert sein.
import yaml


class ConfigError(ValueError):
    """
    Beschreibt einen Verstoß gegen das Basisschema der Konfiguration.

    Die Ausnahme wird vor jedem produktiven Workflowstart ausgelöst.
    Dadurch werden unvollständige oder falsch typisierte Konfigurationen blockiert.
    """


def _canonical(value: Any) -> Any:
    """
    Erstellt eine rekursiv sortierte Darstellung eines Konfigurationswertes.

    Wörterbuchschlüssel werden lexikografisch sortiert.
    Listen behalten ihre Reihenfolge, weil diese semantisch relevant sein kann.
    Der Rückgabewert ist ausschließlich für einen stabilen Fingerprint bestimmt.
    """
    if isinstance(value, dict):
        return {str(key): _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    return value


def config_fingerprint(config: dict[str, Any]) -> str:
    """
    Berechnet den SHA256-Fingerprint der effektiven Konfiguration.

    Die kanonische JSON-Darstellung verhindert abweichende Hashes.
    Der Fingerprint wird in Run-, State- und Manifest-Artefakten verwendet.
    """
    canonical = _canonical(config)
    payload = json.dumps(canonical, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_config(path: str | Path) -> dict[str, Any]:
    """
    Liest eine YAML-Datei und validiert die Konfigurationswurzel.

    Fehler beim Lesen oder bei einem nicht-mappingartigen YAML-Wert werden.
    Als ConfigError gemeldet, damit der Workflow sicher blockiert.
    """
    source = Path(path)
    try:
        value = yaml.safe_load(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"Cannot read configuration: {source}") from exc
    if not isinstance(value, dict):
        raise ConfigError("Configuration root must be a mapping")
    validate_config(value)
    return value


def validate_config(config: dict[str, Any]) -> None:
    """
    Prüft die für die Basisschicht erforderlichen Config-Abschnitte.

    `paths.basedir` ist der normative Name; `base_dir` bleibt als.
    Kompatibilitätsalias für die vorhandene Legacy-Konfiguration zulässig.
    """
    required = {"paths", "safety"}
    missing = sorted(required - config.keys())
    if missing:
        raise ConfigError(f"Missing top-level sections: {', '.join(missing)}")

    paths = config["paths"]
    safety = config["safety"]
    if not isinstance(paths, dict) or not isinstance(safety, dict):
        raise ConfigError("paths and safety must be mappings")

    base = paths.get("basedir", paths.get("base_dir"))
    if not base:
        raise ConfigError("paths.basedir or paths.base_dir is required")
    if not isinstance(base, str):
        raise ConfigError("paths.basedir must be a string")

    for key in ("require_paths_within_base_dir", "follow_symlinks"):
        if key in safety and not isinstance(safety[key], bool):
            raise ConfigError(f"safety.{key} must be boolean")
    if "extensions" in config and not isinstance(config["extensions"], dict):
        raise ConfigError("extensions must be a mapping")


def effective_base_dir(config: dict[str, Any]) -> Path:
    """
    Gibt den expandierten Basispfad der validierten Konfiguration zurück.

    Die Funktion akzeptiert den aktuellen Legacy-Alias `base_dir`.
    Eine fehlende oder ungültige Basiskonfiguration wird durch validate_config.
    Vor der Rückgabe als ConfigError gemeldet.
    """
    validate_config(config)
    base = config["paths"].get("basedir", config["paths"].get("base_dir"))
    return Path(base).expanduser()
