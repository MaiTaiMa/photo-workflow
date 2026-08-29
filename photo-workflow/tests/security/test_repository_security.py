# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/security/test_repository_security.py
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

from app.security_audit import audit_tree


def test_repository_json_has_no_forbidden_runtime_payloads():
    root = Path(__file__).resolve().parents[2]
    findings = audit_tree(root)
    assert findings == {}


def test_security_audit_detects_nested_forbidden_key(tmp_path: Path):
    value = tmp_path / "runtime.json"
    value.write_text(json.dumps({"nested": {"embedding": [1, 2]}}))
    assert audit_tree(tmp_path)