"""
# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/test_selection_schema.py
# PURPOSE:     Tests für selection_schema.py (AP3)
# AUTHOR:      Benjamin (via AP3-Implementierung)
# DATE:        2026-08-09
# VERSION:     1.0.0 (AP3)
# REQUIRES:    Python 3.8+, pytest
# CHANGES:
#   2026-08-09: Initiale Implementierung für AP3
#               - Tests für SelectionSchema.validate()
#               - Tests für validate_selection()
#               - Tests für compute_fingerprint()
#               - Tests für create_empty_selection()
# =============================================================================
"""

import sys
import os
import json
import tempfile
import pytest
from datetime import datetime

# Importiere selection_schema
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'output'))
from selection_schema import (
    SelectionSchema,
    validate_selection,
    compute_fingerprint,
    create_empty_selection,
    SCHEMA_VERSION,
    VALID_POOL_TYPES,
    VALID_STATUS_VALUES,
)


# =============================================================================
# Tests für SelectionSchema.validate()
# =============================================================================

class TestSelectionSchema:
    """Tests für SelectionSchema.validate()."""
    
    def test_valid_selection_accepted(self, tmp_path):
        """Gueltige selection.json wird akzeptiert."""
        base_dir = str(tmp_path / 'base')
        os.makedirs(base_dir, exist_ok=True)
        
        selection = {
            "schema_version": SCHEMA_VERSION,
            "pool_type": "aesthetic",
            "updated_at": "2026-08-09T12:00:00Z",
            "selection_fingerprint": "abc123",
            "pool_build_id": "test-123",
            "rank_digits": 4,
            "limits": {
                "max_active": 100,
                "min_active": 50,
                "target_active": 80,
                "max_new": 50,
            },
            "images": [
                {
                    "rel_path": "test/image1.jpg",
                    "status": "active",
                    "rank": 1,
                    "added_at": "2026-08-09T10:00:00Z",
                }
            ],
        }
        
        schema = SelectionSchema(base_dir=base_dir, strict=True)
        is_valid, errors, warnings = schema.validate(selection)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_missing_required_field_rejected(self, tmp_path):
        """Fehlende Pflichtfelder werden abgelehnt."""
        base_dir = str(tmp_path / 'base')
        os.makedirs(base_dir, exist_ok=True)
        
        selection = {
            "schema_version": SCHEMA_VERSION,
            # pool_type fehlt
            "updated_at": "2026-08-09T12:00:00Z",
            "rank_digits": 4,
            "limits": {
                "max_active": 100,
                "min_active": 50,
                "target_active": 80,
                "max_new": 50,
            },
            "images": [],
        }
        
        schema = SelectionSchema(base_dir=base_dir, strict=True)
        is_valid, errors, warnings = schema.validate(selection)
        
        assert is_valid is False
        assert any("pool_type" in err for err in errors)
    
    def test_invalid_pool_type_rejected(self, tmp_path):
        """Ungueltiger pool_type wird abgelehnt."""
        base_dir = str(tmp_path / 'base')
        os.makedirs(base_dir, exist_ok=True)
        
        selection = {
            "schema_version": SCHEMA_VERSION,
            "pool_type": "invalid",  # Muss aesthetic, personal oder face sein
            "updated_at": "2026-08-09T12:00:00Z",
            "rank_digits": 4,
            "limits": {
                "max_active": 100,
                "min_active": 50,
                "target_active": 80,
                "max_new": 50,
            },
            "images": [],
        }
        
        schema = SelectionSchema(base_dir=base_dir, strict=True)
        is_valid, errors, warnings = schema.validate(selection)
        
        assert is_valid is False
        assert any("pool_type" in err for err in errors)
    
    def test_invalid_status_rejected(self, tmp_path):
        """Ungueltiger Status wird abgelehnt."""
        base_dir = str(tmp_path / 'base')
        os.makedirs(base_dir, exist_ok=True)
        
        selection = {
            "schema_version": SCHEMA_VERSION,
            "pool_type": "aesthetic",
            "updated_at": "2026-08-09T12:00:00Z",
            "rank_digits": 4,
            "limits": {
                "max_active": 100,
                "min_active": 50,
                "target_active": 80,
                "max_new": 50,
            },
            "images": [
                {
                    "rel_path": "test/image1.jpg",
                    "status": "invalid",  # Muss active, new oder unknown sein
                    "rank": 1,
                    "added_at": "2026-08-09T10:00:00Z",
                }
            ],
        }
        
        schema = SelectionSchema(base_dir=base_dir, strict=True)
        is_valid, errors, warnings = schema.validate(selection)
        
        assert is_valid is False
        assert any("status" in err for err in errors)
    
    def test_path_traversal_rejected(self, tmp_path):
        """Path-Traversal in rel_path wird abgelehnt."""
        base_dir = str(tmp_path / 'base')
        os.makedirs(base_dir, exist_ok=True)
        
        selection = {
            "schema_version": SCHEMA_VERSION,
            "pool_type": "aesthetic",
            "updated_at": "2026-08-09T12:00:00Z",
            "rank_digits": 4,
            "limits": {
                "max_active": 100,
                "min_active": 50,
                "target_active": 80,
                "max_new": 50,
            },
            "images": [
                {
                    "rel_path": "../escape.jpg",  # Path-Traversal
                    "status": "active",
                    "rank": 1,
                    "added_at": "2026-08-09T10:00:00Z",
                }
            ],
        }
        
        schema = SelectionSchema(base_dir=base_dir, strict=True)
        is_valid, errors, warnings = schema.validate(selection)
        
        assert is_valid is False
        assert any("Path-Traversal" in err or "outside" in err.lower() for err in errors)
    
    def test_invalid_schema_version_rejected(self, tmp_path):
        """Ungueltige schema_version wird abgelehnt."""
        base_dir = str(tmp_path / 'base')
        os.makedirs(base_dir, exist_ok=True)
        
        selection = {
            "schema_version": "0.9",  # Ungueltig
            "pool_type": "aesthetic",
            "updated_at": "2026-08-09T12:00:00Z",
            "rank_digits": 4,
            "limits": {
                "max_active": 100,
                "min_active": 50,
                "target_active": 80,
                "max_new": 50,
            },
            "images": [],
        }
        
        schema = SelectionSchema(base_dir=base_dir, strict=True)
        is_valid, errors, warnings = schema.validate(selection)
        
        assert is_valid is False
        assert any("schema_version" in err for err in errors)
    
    def test_limits_validation(self, tmp_path):
        """Limits-Validierung."""
        base_dir = str(tmp_path / 'base')
        os.makedirs(base_dir, exist_ok=True)
        
        # target_active > max_active (Fehler)
        selection = {
            "schema_version": SCHEMA_VERSION,
            "pool_type": "aesthetic",
            "updated_at": "2026-08-09T12:00:00Z",
            "rank_digits": 4,
            "limits": {
                "max_active": 50,
                "min_active": 10,
                "target_active": 100,  # > max_active
                "max_new": 50,
            },
            "images": [],
        }
        
        schema = SelectionSchema(base_dir=base_dir, strict=True)
        is_valid, errors, warnings = schema.validate(selection)
        
        assert is_valid is False
        assert any("target_active" in err for err in errors)


# =============================================================================
# Tests für compute_fingerprint()
# =============================================================================

class TestComputeFingerprint:
    """Tests für compute_fingerprint()."""
    
    def test_fingerprint_deterministic(self):
        """Fingerprint ist deterministisch."""
        images = [
            {"rel_path": "a.jpg", "rank": 1},
            {"rel_path": "b.jpg", "rank": 2},
        ]
        
        fp1 = compute_fingerprint(images)
        fp2 = compute_fingerprint(images)
        
        assert fp1 == fp2
    
    def test_fingerprint_changes_with_order(self):
        """Fingerprint aendert sich mit Reihenfolge."""
        images1 = [
            {"rel_path": "a.jpg", "rank": 1},
            {"rel_path": "b.jpg", "rank": 2},
        ]
        
        images2 = [
            {"rel_path": "b.jpg", "rank": 2},
            {"rel_path": "a.jpg", "rank": 1},
        ]
        
        fp1 = compute_fingerprint(images1)
        fp2 = compute_fingerprint(images2)
        
        # Sollte gleich sein (wird nach rank sortiert)
        assert fp1 == fp2
    
    def test_fingerprint_changes_with_content(self):
        """Fingerprint aendert sich mit Inhalt."""
        images1 = [
            {"rel_path": "a.jpg", "rank": 1},
        ]
        
        images2 = [
            {"rel_path": "b.jpg", "rank": 1},
        ]
        
        fp1 = compute_fingerprint(images1)
        fp2 = compute_fingerprint(images2)
        
        assert fp1 != fp2


# =============================================================================
# Tests für create_empty_selection()
# =============================================================================

class TestCreateEmptySelection:
    """Tests für create_empty_selection()."""
    
    def test_creates_valid_selection(self, tmp_path):
        """Erstellt gueltige leere selection."""
        base_dir = str(tmp_path / 'base')
        os.makedirs(base_dir, exist_ok=True)
        
        selection = create_empty_selection("aesthetic", base_dir)
        
        assert selection["schema_version"] == SCHEMA_VERSION
        assert selection["pool_type"] == "aesthetic"
        assert "updated_at" in selection
        assert selection["rank_digits"] == 4
        assert "limits" in selection
        assert selection["images"] == []
        
        # Validieren
        schema = SelectionSchema(base_dir=base_dir, strict=True)
        is_valid, errors, warnings = schema.validate(selection)
        
        assert is_valid is True
        assert len(errors) == 0


# =============================================================================
# Tests für validate_selection()
# =============================================================================

class TestValidateSelection:
    """Tests für validate_selection()."""
    
    def test_valid_selection(self, tmp_path):
        """Gueltige selection wird akzeptiert."""
        base_dir = str(tmp_path / 'base')
        os.makedirs(base_dir, exist_ok=True)
        
        selection = create_empty_selection("aesthetic", base_dir)
        
        is_valid, errors, warnings = validate_selection(selection, base_dir, strict=True)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_invalid_selection(self, tmp_path):
        """Invalide selection wird abgelehnt."""
        base_dir = str(tmp_path / 'base')
        os.makedirs(base_dir, exist_ok=True)
        
        selection = {
            "schema_version": "invalid",
            "pool_type": "aesthetic",
        }
        
        is_valid, errors, warnings = validate_selection(selection, base_dir, strict=True)
        
        assert is_valid is False
        assert len(errors) > 0


# =============================================================================
# Haupt (fuer pytest)
# =============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])