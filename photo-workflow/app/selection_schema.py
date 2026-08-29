# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/selection_schema.py
# PURPOSE:     JSON-Schema und Validierung für selection.json (AP3)
# AUTHOR:      Matzethias
# DATE:        2026-08-09
# VERSION:     1.0.0
# REQUIRES:    Python 3.8+, jsonschema (optional)
# CHANGES:
#   2026-08-09: Initiale Implementierung für AP3
#               - SelectionSchema-Klasse mit Validierung
#               - validate_selection() für selection.json
#               - validate_image_entry() für einzelne Eintraege
#               - compute_fingerprint() für Integritaetspruefung
# =============================================================================


import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path

# Importiere runtime_paths für Pfadvalidierung (AP2)
try:
    from runtime_paths import is_path_within_base, validate_path_safe
except ImportError:
    # Fallback für Tests
    def is_path_within_base(path: str, base_dir: str) -> bool:
        return '..' not in path and path.startswith(base_dir)
    
    def validate_path_safe(path: str, base_dir: str, allow_symlinks: bool = False) -> Tuple[bool, List[str]]:
        if '..' in path:
            return False, ["Path-Traversal"]
        if not path.startswith(base_dir):
            return False, ["Outside base_dir"]
        return True, []


# =============================================================================
# Konstanten
# =============================================================================

SCHEMA_VERSION = "1.0"

VALID_POOL_TYPES = ["aesthetic", "personal", "face"]

VALID_STATUS_VALUES = ["active", "new", "unknown"]

VALID_SOURCES = ["manual", "auto", "migration"]

REQUIRED_TOP_KEYS = [
    "schema_version",
    "pool_type",
    "updated_at",
    "selection_fingerprint",
    "pool_build_id",
    "rank_digits",
    "limits",
    "images",
]

REQUIRED_LIMITS_KEYS = [
    "max_active",
    "min_active",
    "target_active",
    "max_new",
]

REQUIRED_IMAGE_KEYS = [
    "rel_path",
    "status",
    "rank",
    "added_at",
]

OPTIONAL_IMAGE_KEYS = [
    "score",
    "source",
    "metadata",
]


# =============================================================================
# SelectionSchema-Klasse
# =============================================================================

class SelectionSchema:
    """
    Validierung für selection.json.
    """
    
    def __init__(self, base_dir: str, strict: bool = True):
        """
        Initialisiert das Schema.
        
        Args:
            base_dir: Basisverzeichnis für Pfadvalidierung
            strict: Wenn True, unbekannte Felder werden abgelehnt
        """
        self.base_dir = base_dir
        self.strict = strict
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate(self, selection: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Validiert eine selection.json.
        
        Args:
            selection: Geladene selection.json als Dict
        
        Returns:
            Tuple (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        # 1. Top-Level-Schluessel pruefen
        self._validate_top_keys(selection)
        
        # 2. schema_version pruefen
        if "schema_version" in selection:
            self._validate_schema_version(selection["schema_version"])
        
        # 3. pool_type pruefen
        if "pool_type" in selection:
            self._validate_pool_type(selection["pool_type"])
        
        # 4. updated_at pruefen
        if "updated_at" in selection:
            self._validate_updated_at(selection["updated_at"])
        
        # 5. rank_digits pruefen
        if "rank_digits" in selection:
            self._validate_rank_digits(selection["rank_digits"])
        
        # 6. limits pruefen
        if "limits" in selection:
            self._validate_limits(selection["limits"])
        
        # 7. images pruefen
        if "images" in selection:
            self._validate_images(selection["images"])
        
        # 8. selection_fingerprint pruefen (optional, Warnung wenn fehlt)
        if "selection_fingerprint" not in selection:
            self.warnings.append("selection_fingerprint fehlt (empfohlen)")
        
        # 9. pool_build_id pruefen (optional, Warnung wenn fehlt)
        if "pool_build_id" not in selection:
            self.warnings.append("pool_build_id fehlt (empfohlen)")
        
        return len(self.errors) == 0, self.errors, self.warnings
    
    def _validate_top_keys(self, selection: Dict[str, Any]) -> None:
        """Validiert erforderliche Top-Level-Schluessel."""
        for key in REQUIRED_TOP_KEYS:
            if key not in selection:
                self.errors.append(f"Erforderliches Feld '{key}' fehlt")
        
        if self.strict:
            allowed_keys = REQUIRED_TOP_KEYS + ["selection_fingerprint", "pool_build_id"]
            for key in selection.keys():
                if key not in allowed_keys:
                    self.warnings.append(f"Unbekanntes Feld: '{key}'")
    
    def _validate_schema_version(self, version: Any) -> None:
        """Validiert schema_version."""
        if not isinstance(version, str):
            self.errors.append("schema_version muss ein String sein")
        elif version != SCHEMA_VERSION:
            self.errors.append(f"schema_version '{version}' wird nicht unterstuetzt (erwartet: {SCHEMA_VERSION})")
    
    def _validate_pool_type(self, pool_type: Any) -> None:
        """Validiert pool_type."""
        if not isinstance(pool_type, str):
            self.errors.append("pool_type muss ein String sein")
        elif pool_type not in VALID_POOL_TYPES:
            self.errors.append(f"pool_type '{pool_type}' ist ungueltig (erlaubt: {VALID_POOL_TYPES})")
    
    def _validate_updated_at(self, updated_at: Any) -> None:
        """Validiert updated_at (ISO-8601)."""
        if not isinstance(updated_at, str):
            self.errors.append("updated_at muss ein String sein")
        else:
            try:
                # ISO-8601 pruefen
                datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except ValueError:
                self.errors.append(f"updated_at '{updated_at}' ist kein gueltiges ISO-8601 Datum")
    
    def _validate_rank_digits(self, rank_digits: Any) -> None:
        """Validiert rank_digits."""
        if not isinstance(rank_digits, int):
            self.errors.append("rank_digits muss eine Ganzzahl sein")
        elif rank_digits < 1 or rank_digits > 10:
            self.errors.append(f"rank_digits muss zwischen 1 und 10 liegen (ist: {rank_digits})")
    
    def _validate_limits(self, limits: Dict[str, Any]) -> None:
        """Validiert limits."""
        # Erforderliche Schluessel
        for key in REQUIRED_LIMITS_KEYS:
            if key not in limits:
                self.errors.append(f"limits.{key} fehlt")
        
        # Typ- und Wert-Validierung
        for key in REQUIRED_LIMITS_KEYS:
            if key in limits:
                value = limits[key]
                if not isinstance(value, int):
                    self.errors.append(f"limits.{key} muss eine Ganzzahl sein")
                elif value < 0:
                    self.errors.append(f"limits.{key} muss >= 0 sein")
        
        # max_new_per_batch (optional)
        if "max_new_per_batch" in limits:
            value = limits["max_new_per_batch"]
            if not isinstance(value, int):
                self.errors.append("limits.max_new_per_batch muss eine Ganzzahl sein")
            elif value < 1:
                self.errors.append("limits.max_new_per_batch muss >= 1 sein")
        
        # Logik-Validierung
        if "max_active" in limits and "target_active" in limits:
            if limits["target_active"] > limits["max_active"]:
                self.errors.append("limits.target_active darf limits.max_active nicht ueberschreiten")
        
        if "min_active" in limits and "max_active" in limits:
            if limits["min_active"] > limits["max_active"]:
                self.errors.append("limits.min_active darf limits.max_active nicht ueberschreiten")
    
    def _validate_images(self, images: List[Any]) -> None:
        """Validiert images-Array."""
        if not isinstance(images, list):
            self.errors.append("images muss ein Array sein")
            return
        
        ranks_seen = set()
        
        for i, image in enumerate(images):
            if not isinstance(image, dict):
                self.errors.append(f"images[{i}] muss ein Objekt sein")
                continue
            
            # Bild-Eintrag validieren
            self._validate_image_entry(image, i, ranks_seen)
    
    def _validate_image_entry(self, image: Dict[str, Any], index: int, ranks_seen: set) -> None:
        """Validiert einen einzelnen image-Eintrag."""
        prefix = f"images[{index}]"
        
        # Erforderliche Schluessel
        for key in REQUIRED_IMAGE_KEYS:
            if key not in image:
                self.errors.append(f"{prefix}.{key} fehlt")
        
        # rel_path
        if "rel_path" in image:
            rel_path = image["rel_path"]
            if not isinstance(rel_path, str):
                self.errors.append(f"{prefix}.rel_path muss ein String sein")
            elif not rel_path.strip():
                self.errors.append(f"{prefix}.rel_path ist leer")
            else:
                # Pfad gegen base_dir pruefen (AP2-Logik)
                full_path = str(Path(self.base_dir) / rel_path)
                is_valid, path_errors = validate_path_safe(full_path, self.base_dir)
                if not is_valid:
                    self.errors.extend([f"{prefix}.rel_path: {err}" for err in path_errors])
        
        # status
        if "status" in image:
            status = image["status"]
            if not isinstance(status, str):
                self.errors.append(f"{prefix}.status muss ein String sein")
            elif status not in VALID_STATUS_VALUES:
                self.errors.append(f"{prefix}.status '{status}' ist ungueltig (erlaubt: {VALID_STATUS_VALUES})")
        
        # rank
        if "rank" in image:
            rank = image["rank"]
            if not isinstance(rank, int):
                self.errors.append(f"{prefix}.rank muss eine Ganzzahl sein")
            elif rank < 1:
                self.errors.append(f"{prefix}.rank muss >= 1 sein")
            else:
                # Duplikate erkennen
                if rank in ranks_seen:
                    self.warnings.append(f"{prefix}.rank {rank} ist nicht eindeutig")
                ranks_seen.add(rank)
        
        # added_at
        if "added_at" in image:
            added_at = image["added_at"]
            if not isinstance(added_at, str):
                self.errors.append(f"{prefix}.added_at muss ein String sein")
            else:
                try:
                    datetime.fromisoformat(added_at.replace("Z", "+00:00"))
                except ValueError:
                    self.errors.append(f"{prefix}.added_at '{added_at}' ist kein gueltiges ISO-8601 Datum")
        
        # score (optional)
        if "score" in image:
            score = image["score"]
            if not isinstance(score, (int, float)):
                self.errors.append(f"{prefix}.score muss eine Zahl sein")
            elif score < 0 or score > 1:
                self.errors.append(f"{prefix}.score muss zwischen 0 und 1 liegen")
        
        # source (optional)
        if "source" in image:
            source = image["source"]
            if not isinstance(source, str):
                self.errors.append(f"{prefix}.source muss ein String sein")
            elif source not in VALID_SOURCES:
                self.errors.append(f"{prefix}.source '{source}' ist ungueltig (erlaubt: {VALID_SOURCES})")
        
        # metadata (optional)
        if "metadata" in image:
            metadata = image["metadata"]
            if not isinstance(metadata, dict):
                self.errors.append(f"{prefix}.metadata muss ein Objekt sein")
        
        # Unbekannte Felder (strict mode)
        if self.strict:
            allowed_keys = REQUIRED_IMAGE_KEYS + OPTIONAL_IMAGE_KEYS
            for key in image.keys():
                if key not in allowed_keys:
                    self.warnings.append(f"{prefix}. unbekanntes Feld: '{key}'")


# =============================================================================
# Hilfsfunktionen
# =============================================================================

def compute_fingerprint(images: List[Dict[str, Any]]) -> str:
    """
    Berechnet SHA-256 Fingerprint über alle image-entries.
    
    Args:
        images: Liste von image-Dicts
    
    Returns:
        SHA-256 Hash als Hex-String
    """
    # Sortiere images nach rank für deterministischen Hash
    sorted_images = sorted(images, key=lambda x: x.get("rank", 0))
    
    # Erstelle kanonische JSON-Repraeaentation
    canonical = json.dumps(sorted_images, sort_keys=True, separators=(",", ":"))
    
    # SHA-256 berechnen
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_selection(selection: Dict[str, Any], base_dir: str, strict: bool = True) -> Tuple[bool, List[str], List[str]]:
    """
    Validiert eine selection.json (Hilfsfunktion).
    
    Args:
        selection: Geladene selection.json als Dict
        base_dir: Basisverzeichnis für Pfadvalidierung
        strict: Strikter Modus
    
    Returns:
        Tuple (is_valid, errors, warnings)
    """
    schema = SelectionSchema(base_dir=base_dir, strict=strict)
    return schema.validate(selection)


def create_empty_selection(pool_type: str, base_dir: str) -> Dict[str, Any]:
    """
    Erstellt eine leere selection.json-Vorlage.
    
    Args:
        pool_type: Typ des Pools (aesthetic, personal, face)
        base_dir: Basisverzeichnis
    
    Returns:
        Leere selection.json als Dict
    """
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    return {
        "schema_version": SCHEMA_VERSION,
        "pool_type": pool_type,
        "updated_at": now,
        "selection_fingerprint": "",  # Wird nach Befuellen berechnet
        "pool_build_id": f"{now.replace(':', '').replace('-', '').replace('.', '')}-{pool_type}",
        "rank_digits": 4,
        "limits": {
            "max_active": 100,
            "min_active": 50,
            "target_active": 80,
            "max_new": 50,
            "max_new_per_batch": 10,
        },
        "images": [],
    }