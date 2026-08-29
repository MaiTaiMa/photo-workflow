# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_package_imports.py
# PURPOSE:     Sichert paketrelative Importe der Workflow-Module ab.
# AUTHOR:      Matzethias
# DATE:        2026-08-20
# VERSION:     1.0.0
# REQUIRES:    Python 3.11, pytest
# CHANGES:
#   2026-08-20 | 1.0.0 | I1: Regressionstest für Best-of- und Workflow-Paketimporte.
# =============================================================================


import importlib


def test_best_of_selection_imports_as_package_module() -> None:
    module = importlib.import_module("app.best_of_selection")

    assert module.SelectionResult.__name__ == "SelectionResult"


def test_photo_workflow_imports_as_package_module() -> None:
    module = importlib.import_module("app.photo_workflow")

    assert callable(module.load_config)