# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/embedding_cache.py
# PURPOSE:     Embedding-Cache-Verwaltung (AP6)
# AUTHOR:      Matzethias
# DATE:        2026-08-09
# VERSION:     1.0.0
# REQUIRES:    Python 3.8+, json
# CHANGES:
#   2026-08-09: Initiale Implementierung für AP6
# =============================================================================


import json
import os
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path


# =============================================================================
# EmbeddingCache-Klasse
# =============================================================================

class EmbeddingCache:
    """
    Cache für CLIP-Embeddings.
    """
    
    def __init__(self, cache_path: str, pool_type: str):
        """
        Initialisiert Embedding-Cache.
        
        Args:
            cache_path: Pfad zur Cache-Datei
            pool_type: Typ des Pools (aesthetic, personal, face)
        """
        self.cache_path = cache_path
        self.pool_type = pool_type
        self.cache: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}
        
        # Cache laden (wenn vorhanden)
        if os.path.exists(cache_path):
            self.load_cache()
    
    def load_cache(self) -> None:
        """Laedt Cache aus Datei."""
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.cache = data.get("embeddings", {})
                self.metadata = data.get("metadata", {})
        except (json.JSONDecodeError, IOError) as e:
            # Fehler: leeren Cache
            self.cache = {}
            self.metadata = {}
    
    def save_cache(self) -> None:
        """Speichert Cache in Datei."""
        # Parent-Verzeichnis sicherstellen
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        
        data = {
            "embeddings": self.cache,
            "metadata": self.metadata,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
        
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_embedding(self, image_path: str) -> Optional[List[float]]:
        """
        Gibt Cached-Embedding zurueck.
        
        Args:
            image_path: Pfad zum Bild
        
        Returns:
            Embedding (Liste von Floats) oder None
        """
        # Hash des Pfades
        path_hash = self._compute_path_hash(image_path)
        
        # Cache-Eintrag
        entry = self.cache.get(path_hash)
        
        if entry is None:
            return None
        
        # Gueltigkeit pruefen
        if not self._is_valid_entry(entry):
            return None
        
        return entry.get("embedding")
    
    def cache_embedding(self, image_path: str, embedding: List[float],
                       metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Speichert Embedding im Cache.
        
        Args:
            image_path: Pfad zum Bild
            embedding: Embedding (Liste von Floats)
            metadata: Optionale Metadaten
        """
        # Hash des Pfades
        path_hash = self._compute_path_hash(image_path)
        
        # Eintrag
        entry = {
            "embedding": embedding,
            "cached_at": datetime.utcnow().isoformat() + "Z",
            "image_path": image_path,
        }
        
        if metadata:
            entry["metadata"] = metadata
        
        # Speichern
        self.cache[path_hash] = entry
    
    def invalidate(self) -> None:
        """
        Invalidiert gesamten Cache.
        """
        self.cache = {}
        self.metadata = {
            "invalidated_at": datetime.utcnow().isoformat() + "Z",
            "reason": "manual_invalidation",
        }
        
        # Cache-Datei loeschen
        if os.path.exists(self.cache_path):
            os.remove(self.cache_path)
    
    def invalidate_single(self, image_path: str) -> None:
        """
        Invalidiert einzelnes Embedding.
        
        Args:
            image_path: Pfad zum Bild
        """
        path_hash = self._compute_path_hash(image_path)
        
        if path_hash in self.cache:
            del self.cache[path_hash]
    
    def _compute_path_hash(self, image_path: str) -> str:
        """
        Berechnet Hash für Bildpfad.
        
        Args:
            image_path: Pfad zum Bild
        
        Returns:
            SHA-256 Hash (erste 16 Zeichen)
        """
        canonical = os.path.normpath(image_path)
        hash_hex = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return hash_hex[:16]
    
    def _is_valid_entry(self, entry: Dict[str, Any]) -> bool:
        """
        Prueft Gueltigkeit eines Cache-Eintrags.
        
        Args:
            entry: Cache-Eintrag
        
        Returns:
            True, wenn gueltig
        """
        # Embedding vorhanden?
        if "embedding" not in entry:
            return False
        
        # cached_at vorhanden?
        if "cached_at" not in entry:
            return False
        
        # Alters-Check: Optional (z.B. 7 Tage) - Implementierung nach Bedarf
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Gibt Cache-Statistiken zurueck.
        
        Returns:
            Dict mit Statistiken
        """
        return {
            "pool_type": self.pool_type,
            "cache_path": self.cache_path,
            "num_embeddings": len(self.cache),
            "metadata": self.metadata,
        }


# =============================================================================
# Cache-Verwaltung
# =============================================================================

def get_cache_path(pool_type: str, base_dir: str) -> str:
    """
    Gibt Cache-Pfad für Pool zurueck.
    
    Args:
        pool_type: Typ des Pools
        base_dir: Basisverzeichnis
    
    Returns:
        Pfad zur Cache-Datei
    """
    if pool_type == "aesthetic":
        cache_dir = os.path.join(base_dir, "WORKFLOW_DATA", "models", "reference_scoring")
    elif pool_type == "personal":
        cache_dir = os.path.join(base_dir, "WORKFLOW_DATA", "models", "taste")
    else:
        cache_dir = os.path.join(base_dir, "WORKFLOW_DATA", "models", "family_faces")
    
    return os.path.join(cache_dir, "embeddings_cache.json")


def invalidate_pool_cache(pool_type: str, base_dir: str) -> None:
    """
    Invalidiert Cache für Pool.
    
    Args:
        pool_type: Typ des Pools
        base_dir: Basisverzeichnis
    """
    cache_path = get_cache_path(pool_type, base_dir)
    
    if os.path.exists(cache_path):
        os.remove(cache_path)


def load_or_create_cache(pool_type: str, base_dir: str) -> EmbeddingCache:
    """
    Laedt oder erstellt Cache.
    
    Args:
        pool_type: Typ des Pools
        base_dir: Basisverzeichnis
    
    Returns:
        EmbeddingCache-Instanz
    """
    cache_path = get_cache_path(pool_type, base_dir)
    return EmbeddingCache(cache_path, pool_type)