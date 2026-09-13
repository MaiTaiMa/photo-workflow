"""F12: AUTO-VALIDATE-Skip meldet Umbenennungs-Risiko statt leise zu bleiben."""
from pathlib import Path


def test_auto_validate_skip_warns_about_rename():
    src = Path("app/photo_workflow.py").read_text(encoding="utf-8")
    assert "uebersprungen: keine Predictions gefunden" in src
    assert "umbenannt" in src
    assert "uebersprungen: keine Predictions\")" not in src
