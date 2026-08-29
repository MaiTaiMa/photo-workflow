# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_style_audit.py
# PURPOSE:     Prüft die Kernregeln des AP22.0-Regelaudits.
# AUTHOR:      Matzethias
# DATE:        2026-08-08
# VERSION:     1.0
# REQUIRES:    Python 3.11+, pytest
# CHANGES:
#   2026-08-08 | 1.0 | Initiale AP22.0-Audit-Tests
# =============================================================================


from __future__ import annotations

import json
from pathlib import Path

from tools.style_audit import audit_json, audit_script


def test_script_audit_accepts_compliant_fixture(tmp_path: Path):
    path = tmp_path / "fixture.py"
    path.write_text('''"""\nSkript: fixture.py\nZweck: Test\nVersion: 1.0\nÄnderungsprotokoll:\n  2026-08-08 | 1.0 | Test\n"""\n\n# Abschnitt\n# Zweck\n# Hinweis\n\ndef run():\n    """Testfunktion."""\n    # Aktion\n    # Ergebnis\n    return True\n''')
    assert "line_over_100_characters" not in audit_script(path)


def test_json_audit_detects_forbidden_payload(tmp_path: Path):
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"schema_version": 1, "producer_version": "test",
                                "embedding": [1, 2]}))
    assert any(item.startswith("forbidden_field:") for item in audit_json(path))