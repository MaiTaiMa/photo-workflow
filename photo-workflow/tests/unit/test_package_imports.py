"""
Skript: tests/unit/test_package_imports.py
Zweck: Sichert paketrelative Importe der Workflow-Module ab.
Autor: MaiTaiMa
Erstellt: 2026-08-20
Version: 1.0.0
Requires: Python 3.11, pytest

Änderungsprotokoll:
  2026-08-20 | 1.0.0 | I1: Regressionstest für Best-of- und Workflow-Paketimporte.
"""

import importlib


def test_best_of_selection_imports_as_package_module() -> None:
    module = importlib.import_module("app.best_of_selection")

    assert module.SelectionResult.__name__ == "SelectionResult"


def test_photo_workflow_imports_as_package_module() -> None:
    module = importlib.import_module("app.photo_workflow")

    assert callable(module.load_config)
