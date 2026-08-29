# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/security_audit.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


from __future__ import annotations

import json
from pathlib import Path


FORBIDDEN_KEYS = {"embedding", "embeddings", "image_bytes", "session_token",
                  "password", "api_key"}


def audit_json_file(path: str | Path) -> list[str]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    findings = []
    def walk(node, location="$"):
        if isinstance(node, dict):
            for key, child in node.items():
                if str(key).lower() in FORBIDDEN_KEYS:
                    findings.append(f"{location}.{key}")
                walk(child, f"{location}.{key}")
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, f"{location}[{index}]")
    walk(value)
    return findings


def audit_tree(root: str | Path) -> dict[str, list[str]]:
    result = {}
    for path in Path(root).rglob("*.json"):
        findings = audit_json_file(path)
        if findings:
            result[str(path)] = findings
    return result