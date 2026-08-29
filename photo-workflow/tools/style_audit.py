# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tools/style_audit.py
# PURPOSE:     Prüft projektweite Implementierungs- und JSON-Artefaktregeln.
# AUTHOR:      Matzethias
# DATE:        2026-08-08
# VERSION:     1.0
# REQUIRES:    Python 3.11
# CHANGES:
#   2026-08-08 | 1.0 | Initialer AP22.0-Regelaudit
# =============================================================================


from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


HEADER_MARKERS = ("Skript:", "Zweck:", "Version:", "Änderungsprotokoll:")
JSON_REQUIRED = {"schema_version", "producer_version"}
FORBIDDEN_JSON_KEYS = {"embedding", "embeddings", "image_bytes", "password", "api_key"}


def _header_issues(path: Path, lines: list[str]) -> list[str]:
    """Prüft Headerlänge, Pflichtmarker und Versionsnummer einer Skriptdatei."""
    issues = []
    header = "\n".join(lines[:12])
    if len(lines) < 6 or not all(marker in header for marker in HEADER_MARKERS):
        issues.append("missing_or_incomplete_header")
    if not re.search(r"Version:\s*[0-9]+\.[0-9]+", header):
        issues.append("missing_version")
    return issues


def _comment_issues(lines: list[str]) -> list[str]:
    """Ermittelt grobe Hinweise auf fehlende Abschnitts- und Funktionskommentare."""
    issues = []
    function_count = sum(1 for line in lines if re.match(r"\s*(async\s+)?def\s+", line))
    comment_count = sum(1 for line in lines if line.lstrip().startswith("#"))
    if function_count and comment_count < function_count * 2:
        issues.append("low_comment_density_near_functions")
    return issues


def audit_script(path: Path, max_line_length: int = 100) -> list[str]:
    """Prüft eine Python- oder Bash-Datei ohne deren Inhalt zu verändern."""
    lines = path.read_text(encoding="utf-8").splitlines()
    issues = _header_issues(path, lines)
    issues.extend(_comment_issues(lines))
    if any(len(line) > max_line_length for line in lines):
        issues.append("line_over_100_characters")
    if not any("CHANGELOG" in line or "Änderungsprotokoll" in line for line in lines[:20]):
        issues.append("missing_change_history_reference")
    return sorted(set(issues))


def _walk_json(value, location: str = "$") -> list[str]:
    """Sucht rekursiv nach verbotenen JSON-Feldern und gibt deren Pfade zurück."""
    findings = []
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_JSON_KEYS:
                findings.append(f"{location}.{key}")
            findings.extend(_walk_json(child, f"{location}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_walk_json(child, f"{location}[{index}]"))
    return findings


def audit_json(path: Path) -> list[str]:
    """Prüft JSON-Artefakte auf Pflichtfelder und persistierte geschützte Daten."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ["invalid_json"]
    issues = [f"missing_{key}" for key in JSON_REQUIRED - value.keys()] if isinstance(value, dict) else ["json_root_not_object"]
    issues.extend(f"forbidden_field:{item}" for item in _walk_json(value))
    return sorted(set(issues))


def run(root: Path) -> dict[str, dict[str, list[str]]]:
    """Führt den Audit für Skripte und JSON-Artefakte unterhalb des Projektroots aus."""
    report = {"scripts": {}, "json": {}}
    for path in root.rglob("*"):
        if not path.is_file() or any(part in {".git", ".venv", "__pycache__"} for part in path.parts):
            continue
        if path.suffix in {".py", ".sh"}:
            issues = audit_script(path)
            if issues:
                report["scripts"][str(path.relative_to(root))] = issues
        elif path.suffix == ".json":
            issues = audit_json(path)
            if issues:
                report["json"][str(path.relative_to(root))] = issues
    return report


def main() -> int:
    """Liest CLI-Argumente, schreibt den Audit-Report nach stdout und liefert Exit 1 bei Befunden."""
    parser = argparse.ArgumentParser(description="Audit für 98AP-Implementierungsregeln")
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    report = run(args.root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if any(report.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())