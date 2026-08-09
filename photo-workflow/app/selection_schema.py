"""
# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/selection_schema.py
# PURPOSE:     JSON-Schema und Validierung für selection.json (AP3)
# AUTHOR:      Benjamin (via AP3-Implementierung)
# DATE:        2026-08-09
# VERSION:     1.0.0 (AP3)
# REQUIRES:    Python 3.8+, jsonschema (optional)
# CHANGES:
#   2026-08-09: Initiale Implementierung für AP3
# =============================================================================
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path

SCHEMA_VERSION = "1.0"
VALID_POOL_TYPES = ["aesthetic", "personal", "face"]
VALID_STATUS_VALUES = ["active", "new", "unknown"]
REQUIRED_TOP_KEYS = ["schema_version", "pool_type", "updated_at", "selection_fingerprint", "pool_build_id", "rank_digits", "limits", "images"]
REQUIRED_LIMITS_KEYS = ["max_active", "min_active", "target_active", "max_new"]
REQUIRED_IMAGE_KEYS = ["rel_path", "status", "rank", "added_at"]

class SelectionSchema:
    def __init__(self, base_dir: str, strict: bool = True):
        self.base_dir = base_dir
        self.strict = strict
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate(self, selection: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        self.errors = []
        self.warnings = []
        for key in REQUIRED_TOP_KEYS:
            if key not in selection:
                self.errors.append(f"Erforderliches Feld '{key}' fehlt")
        if "schema_version" in selection and selection["schema_version"] != SCHEMA_VERSION:
            self.errors.append(f"schema_version '{selection['schema_version']}' wird nicht unterstuetzt (erwartet: {SCHEMA_VERSION})")
        if "pool_type" in selection and selection["pool_type"] not in VALID_POOL_TYPES:
            self.errors.append(f"pool_type '{selection['pool_type']}' ist ungueltig (erlaubt: {VALID_POOL_TYPES})")
        if "limits" in selection:
            for key in REQUIRED_LIMITS_KEYS:
                if key not in selection["limits"]:
                    self.errors.append(f"limits.{key} fehlt")
        if "images" in selection and isinstance(selection["images"], list):
            for i, img in enumerate(selection["images"]):
                if not isinstance(img, dict):
                    self.errors.append(f"images[{i}] muss ein Objekt sein")
                else:
                    for key in REQUIRED_IMAGE_KEYS:
                        if key not in img:
                            self.errors.append(f"images[{i}].{key} fehlt")
                    if "status" in img and img["status"] not in VALID_STATUS_VALUES:
                        self.errors.append(f"images[{i}].status '{img['status']}' ist ungueltig")
        return len(self.errors) == 0, self.errors, self.warnings

def validate_selection(selection: Dict[str, Any], base_dir: str, strict: bool = True) -> Tuple[bool, List[str], List[str]]:
    schema = SelectionSchema(base_dir=base_dir, strict=strict)
    return schema.validate(selection)

def compute_fingerprint(images: List[Dict[str, Any]]) -> str:
    sorted_images = sorted(images, key=lambda x: x.get("rank", 0))
    canonical = json.dumps(sorted_images, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def create_empty_selection(pool_type: str, base_dir: str) -> Dict[str, Any]:
    now = datetime.utcnow().isoformat() + "Z"
    return {
        "schema_version": SCHEMA_VERSION,
        "pool_type": pool_type,
        "updated_at": now,
        "selection_fingerprint": "",
        "pool_build_id": f"{now.replace(':', '').replace('-', '').replace('.', '')}-{pool_type}",
        "rank_digits": 4,
        "limits": {"max_active": 100, "min_active": 50, "target_active": 80, "max_new": 50, "max_new_per_batch": 10},
        "images": [],
    }
