# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/selection_pool.py
# PURPOSE:     Pool-Verwaltung für selection.json (AP3)
# AUTHOR:      Matzethias
# DATE:        2026-08-09
# VERSION:     1.0.0
# REQUIRES:    Python 3.8+, selection_schema.py
# CHANGES:
#   2026-08-09: Initiale Implementierung für AP3
# =============================================================================


import json
import os
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path

# Importiere selection_schema
try:
    from selection_schema import (
        SelectionSchema,
        validate_selection,
        compute_fingerprint,
        create_empty_selection,
        SCHEMA_VERSION,
    )
except ImportError:
    # Fallback für Tests (wenn selection_schema.py nicht im Pfad)
    SCHEMA_VERSION = "1.0"
    def validate_selection(selection, base_dir, strict=True):
        return True, [], []
    def compute_fingerprint(images):
        import hashlib
        return hashlib.sha256(json.dumps(images, sort_keys=True).encode()).hexdigest()
    def create_empty_selection(pool_type, base_dir):
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


# =============================================================================
# SelectionPool-Klasse
# =============================================================================

class SelectionPool:
    """
    Verwaltung eines Referenzpools (aesthetic, personal, face).
    """
    
    def __init__(self, pool_path: str, base_dir: str, pool_type: str):
        """
        Initialisiert einen Pool.
        
        Args:
            pool_path: Pfad zum Pool-Verzeichnis (z.B. WORKFLOW_DATA/samples/aesthetic_reference)
            base_dir: Basisverzeichnis (z.B. /path/to/NAS_EXAMPLE)
            pool_type: Typ des Pools (aesthetic, personal, face)
        """
        self.pool_path = pool_path
        self.base_dir = base_dir
        self.pool_type = pool_type
        self.selection_path = os.path.join(pool_path, "selection.json")
        self.selection: Optional[Dict[str, Any]] = None
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def load(self) -> Tuple[bool, List[str]]:
        """
        Laedt selection.json aus dem Pool-Verzeichnis.
        
        Returns:
            Tuple (success, errors)
        """
        self.errors = []
        self.warnings = []
        
        # 1. Datei existiert?
        if not os.path.exists(self.selection_path):
            self.errors.append(f"selection.json nicht gefunden: {self.selection_path}")
            return False, self.errors
        
        # 2. Datei lesen
        try:
            with open(self.selection_path, "r", encoding="utf-8") as f:
                self.selection = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"selection.json ist kein gueltiges JSON: {e}")
            return False, self.errors
        except IOError as e:
            self.errors.append(f"Fehler beim Lesen von selection.json: {e}")
            return False, self.errors
        
        # 3. Validieren
        is_valid, errors, warnings = validate_selection(self.selection, self.base_dir, strict=True)
        self.errors.extend(errors)
        self.warnings.extend(warnings)
        
        if not is_valid:
            return False, self.errors
        
        return True, self.errors
    
    def save(self, update_fingerprint: bool = True) -> Tuple[bool, List[str]]:
        """
        Speichert selection.json im Pool-Verzeichnis.
        
        Args:
            update_fingerprint: Wenn True, Fingerprint vor Speichern aktualisieren
        
        Returns:
            Tuple (success, errors)
        """
        self.errors = []
        
        if self.selection is None:
            self.errors.append("Keine selection geladen (zuerst load() oder create() aufrufen)")
            return False, self.errors
        
        # 1. Fingerprint aktualisieren
        if update_fingerprint:
            self.selection["selection_fingerprint"] = compute_fingerprint(self.selection.get("images", []))
            self.selection["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        # 2. Validieren
        is_valid, errors, warnings = validate_selection(self.selection, self.base_dir, strict=True)
        self.errors.extend(errors)
        self.warnings.extend(warnings)
        
        if not is_valid:
            return False, self.errors
        
        # 3. Speichern
        try:
            # Parent-Verzeichnis sicherstellen
            os.makedirs(os.path.dirname(self.selection_path), exist_ok=True)
            
            with open(self.selection_path, "w", encoding="utf-8") as f:
                json.dump(self.selection, f, indent=2, ensure_ascii=False)
        except IOError as e:
            self.errors.append(f"Fehler beim Schreiben von selection.json: {e}")
            return False, self.errors
        
        return True, self.errors
    
    def create(self, limits: Optional[Dict[str, int]] = None) -> Tuple[bool, List[str]]:
        """
        Erstellt eine neue leere selection.json.
        
        Args:
            limits: Optionale Limits (default: Standardwerte)
        
        Returns:
            Tuple (success, errors)
        """
        self.selection = create_empty_selection(self.pool_type, self.base_dir)
        
        if limits:
            for key in ["max_active", "min_active", "target_active", "max_new", "max_new_per_batch"]:
                if key in limits:
                    self.selection["limits"][key] = limits[key]
        
        return True, []
    
    def add_image(self, rel_path: str, status: str = "new", rank: Optional[int] = None, 
                  score: Optional[float] = None, source: str = "auto") -> Tuple[bool, List[str]]:
        """
        Fuegt ein Bild zur selection hinzu.
        
        Args:
            rel_path: Relativer Pfad zum Bild (von base_dir aus)
            status: Status (active, new, unknown)
            rank: Rang (optional, wird automatisch vergeben wenn None)
            score: Score (optional)
            source: Quelle (manual, auto, migration)
        
        Returns:
            Tuple (success, errors)
        """
        self.errors = []
        
        if self.selection is None:
            self.errors.append("Keine selection geladen")
            return False, self.errors
        
        # 1. Hoechsten existierenden Rank finden
        images = self.selection.get("images", [])
        max_rank = max([img.get("rank", 0) for img in images], default=0)
        
        if rank is None:
            rank = max_rank + 1
        
        # 2. Neuen Eintrag erstellen
        now = datetime.utcnow().isoformat() + "Z"
        new_image = {
            "rel_path": rel_path,
            "status": status,
            "rank": rank,
            "added_at": now,
            "source": source,
        }
        
        if score is not None:
            new_image["score"] = score
        
        # 3. Einfuegen
        images.append(new_image)
        self.selection["images"] = images
        
        return True, self.errors
    
    def remove_image(self, rel_path: str) -> Tuple[bool, List[str]]:
        """
        Entfernt ein Bild aus der selection.
        
        Args:
            rel_path: Relativer Pfad zum Bild
        
        Returns:
            Tuple (success, errors)
        """
        self.errors = []
        
        if self.selection is None:
            self.errors.append("Keine selection geladen")
            return False, self.errors
        
        images = self.selection.get("images", [])
        original_count = len(images)
        
        # Filtere Bild mit rel_path heraus
        self.selection["images"] = [img for img in images if img.get("rel_path") != rel_path]
        
        if len(self.selection["images"]) == original_count:
            self.errors.append(f"Bild {rel_path} nicht gefunden")
            return False, self.errors
        
        return True, self.errors
    
    def get_active_images(self) -> List[Dict[str, Any]]:
        """
        Gibt alle aktiven Bilder zurueck.
        
        Returns:
            Liste von image-Dicts (sortiert nach rank)
        """
        if self.selection is None:
            return []
        
        images = [img for img in self.selection.get("images", []) if img.get("status") == "active"]
        return sorted(images, key=lambda x: x.get("rank", 0))
    
    def get_new_images(self) -> List[Dict[str, Any]]:
        """
        Gibt alle neuen Vorschlaege zurueck.
        
        Returns:
            Liste von image-Dicts (sortiert nach rank)
        """
        if self.selection is None:
            return []
        
        images = [img for img in self.selection.get("images", []) if img.get("status") == "new"]
        return sorted(images, key=lambda x: x.get("rank", 0))
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Gibt Statistiken ueber den Pool zurueck.
        
        Returns:
            Dict mit Statistiken
        """
        if self.selection is None:
            return {"error": "Keine selection geladen"}
        
        images = self.selection.get("images", [])
        active_count = len([img for img in images if img.get("status") == "active"])
        new_count = len([img for img in images if img.get("status") == "new"])
        unknown_count = len([img for img in images if img.get("status") == "unknown"])
        
        limits = self.selection.get("limits", {})
        max_active = limits.get("max_active", 0)
        target_active = limits.get("target_active", 0)
        
        return {
            "pool_type": self.pool_type,
            "total_images": len(images),
            "active_count": active_count,
            "new_count": new_count,
            "unknown_count": unknown_count,
            "max_active": max_active,
            "target_active": target_active,
            "is_full": active_count >= max_active,
            "needs_attention": active_count < limits.get("min_active", 0),
        }


# =============================================================================
# Hilfsfunktionen
# =============================================================================

def load_pool(pool_path: str, base_dir: str, pool_type: str) -> SelectionPool:
    """
    Laedt einen Pool aus dem Dateisystem.
    
    Args:
        pool_path: Pfad zum Pool-Verzeichnis
        base_dir: Basisverzeichnis
        pool_type: Typ des Pools
    
    Returns:
        SelectionPool-Instanz (geladen)
    """
    pool = SelectionPool(pool_path, base_dir, pool_type)
    pool.load()
    return pool


def create_pool(pool_path: str, base_dir: str, pool_type: str, 
                limits: Optional[Dict[str, int]] = None) -> SelectionPool:
    """
    Erstellt einen neuen Pool.
    
    Args:
        pool_path: Pfad zum Pool-Verzeichnis
        base_dir: Basisverzeichnis
        pool_type: Typ des Pools
        limits: Optionale Limits
    
    Returns:
        SelectionPool-Instanz (neu erstellt)
    """
    pool = SelectionPool(pool_path, base_dir, pool_type)
    pool.create(limits=limits)
    pool.save()
    return pool