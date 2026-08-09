"""
Skript: app/config_schema.py
Zweck: Lädt, validiert und fingerprintet die Workflow-Konfiguration.
Autor: MaiTaiMa
Erstellt: 2026-08-08
Version: 1.2
Requires: Python 3.11, PyYAML

Änderungsprotokoll:
  2026-08-08 | 1.1 | AP22.1 Header, Kommentare und Formatierung ergänzt
  2026-08-08 | 1.2 | Lokale Modellkonfiguration und YuNet-Skalierung validiert
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
        return {
            str(key): _canonical(value[key])
            for key in sorted(value)
        }
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
    payload = json.dumps(
        canonical,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_config(path: str | Path) -> dict[str, Any]:
    """
    Liest eine YAML-Datei und validiert die Konfigurationswurzel.

    Fehler beim Lesen oder bei einem nicht-mappingartigen YAML-Wert werden
    als ConfigError gemeldet, damit der Workflow sicher blockiert.
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


def _require_mapping(
    value: Any,
    name: str,
) -> dict[str, Any]:
    """
    Erzwingt eine Mapping-Struktur für einen Config-Abschnitt.

    Die Funktion liefert das geprüfte Mapping zurück.
    Bei einem anderen Datentyp wird die Config sicher abgelehnt.
    """
    if not isinstance(value, dict):
        raise ConfigError(f"{name} must be a mapping")
    return value


def _require_string(
    mapping: dict[str, Any],
    key: str,
    name: str,
) -> str:
    """
    Prüft, ob ein Pflichtschlüssel einen nichtleeren String enthält.

    Leere Modellpfade, Backends und Metriknamen werden abgelehnt.
    """
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{name}.{key} must be a non-empty string")
    return value


def _validate_unit_float(
    mapping: dict[str, Any],
    key: str,
    name: str,
) -> None:
    """
    Prüft einen optionalen Fließkommawert im Intervall 0.0 bis 1.0.

    Boolean-Werte werden ausdrücklich ausgeschlossen, weil bool in Python
    technisch als int-Untertyp behandelt wird.
    """
    if key not in mapping:
        return

    value = mapping[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{name}.{key} must be a number")

    if not 0.0 <= float(value) <= 1.0:
        raise ConfigError(f"{name}.{key} must be between 0.0 and 1.0")


def _validate_positive_int(
    mapping: dict[str, Any],
    key: str,
    name: str,
) -> None:
    """
    Prüft einen optionalen positiven Ganzzahlwert.

    Boolean-Werte werden nicht als gültige Ganzzahlen akzeptiert.
    """
    if key not in mapping:
        return

    value = mapping[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{name}.{key} must be an integer")

    if value <= 0:
        raise ConfigError(f"{name}.{key} must be greater than zero")


def _validate_face_detection(config: dict[str, Any]) -> None:
    """
    Prüft die optionale YuNet-Konfiguration.

    Modellpfad, Backend, Schwellwerte und Eingangsgrößen werden validiert.
    Die Existenz des Modellpfades wird erst beim Modellstart geprüft.
    """
    section = _require_mapping(
        config["models"].get("face_detection"),
        "models.face_detection",
    )

    _require_string(section, "backend", "models.face_detection")
    _require_string(section, "model_path", "models.face_detection")

    _validate_unit_float(
        section,
        "confidence_threshold",
        "models.face_detection",
    )
    _validate_unit_float(
        section,
        "nms_threshold",
        "models.face_detection",
    )
    _validate_positive_int(
        section,
        "top_k",
        "models.face_detection",
    )
    _validate_positive_int(
        section,
        "max_input_side",
        "models.face_detection",
    )


def _validate_face_recognition(config: dict[str, Any]) -> None:
    """
    Prüft die optionale SFace-Konfiguration.

    Modellpfad, Backend, Distanzmetrik und Match-Toleranz werden validiert.
    Die fachliche Kalibrierung der Toleranz bleibt Aufgabe des Adapters.
    """
    section = _require_mapping(
        config["models"].get("face_recognition"),
        "models.face_recognition",
    )

    _require_string(section, "backend", "models.face_recognition")
    _require_string(section, "model_path", "models.face_recognition")

    if "distance_metric" in section:
        metric = section["distance_metric"]
        if metric not in {"cosine", "l2"}:
            raise ConfigError(
                "models.face_recognition.distance_metric "
                "must be cosine or l2"
            )

    _validate_unit_float(
        section,
        "match_tolerance",
        "models.face_recognition",
    )


def _validate_culling_model(config: dict[str, Any]) -> None:
    """
    Prüft die optionale Konfiguration des lokalen Culling-Modells.

    Gewichtsdatei, Architekturdefinition und Preprocessing-Pfad werden
    als nichtleere Zeichenketten validiert.
    """
    section = _require_mapping(
        config["models"].get("culling"),
        "models.culling",
    )

    _require_string(section, "backend", "models.culling")
    _require_string(section, "model_path", "models.culling")
    _require_string(section, "model_config_path", "models.culling")
    _require_string(
        section,
        "processor_config_path",
        "models.culling",
    )


def _validate_models(config: dict[str, Any]) -> None:
    """
    Prüft den optionalen models-Abschnitt.

    Der Abschnitt bleibt optional, damit bestehende Minimal- und
    Basiskonfigurationen weiterhin validiert werden können.
    Sobald models vorhanden ist, werden alle drei Modellbereiche verlangt.
    """
    if "models" not in config:
        return

    models = _require_mapping(config["models"], "models")
    required = {"face_detection", "face_recognition", "culling"}
    missing = sorted(required - models.keys())

    if missing:
        raise ConfigError(
            "Missing model sections: "
            + ", ".join(f"models.{key}" for key in missing)
        )

    _validate_face_detection(config)
    _validate_face_recognition(config)
    _validate_culling_model(config)


def validate_config(config: dict[str, Any]) -> None:
    """
    Prüft die erforderlichen Config-Abschnitte und Modellbereiche.

    `paths.basedir` ist der normative Name.
    `paths.base_dir` bleibt als Kompatibilitätsalias für die Legacy-
    Konfiguration zulässig.
    """
    required = {"paths", "safety"}
    missing = sorted(required - config.keys())

    if missing:
        raise ConfigError(
            f"Missing top-level sections: {', '.join(missing)}"
        )

    paths = _require_mapping(config["paths"], "paths")
    safety = _require_mapping(config["safety"], "safety")

    base = paths.get("basedir", paths.get("base_dir"))
    if not base:
        raise ConfigError(
            "paths.basedir or paths.base_dir is required"
        )

    if not isinstance(base, str):
        raise ConfigError(
            "paths.basedir or paths.base_dir must be a string"
        )

    for key in (
        "require_paths_within_base_dir",
        "follow_symlinks",
        "never_delete_outside_arw_dir",
    ):
        if key in safety and not isinstance(safety[key], bool):
            raise ConfigError(f"safety.{key} must be boolean")

    if "extensions" in config:
        _require_mapping(config["extensions"], "extensions")

    _validate_models(config)


def effective_base_dir(config: dict[str, Any]) -> Path:
    """
    Gibt den expandierten Basispfad der validierten Konfiguration zurück.

    Die Funktion akzeptiert den aktuellen Legacy-Alias `base_dir`.
    Eine fehlende oder ungültige Basiskonfiguration wird durch
    validate_config als ConfigError gemeldet.
    """
    validate_config(config)
    base = config["paths"].get(
        "basedir",
        config["paths"].get("base_dir"),
    )
    return Path(base).expanduser()