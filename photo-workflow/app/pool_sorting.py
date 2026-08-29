# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/pool_sorting.py
# PURPOSE:     Sortierung nach Pool-Nutzen (AP4)
# AUTHOR:      Matzethias
# DATE:        2026-08-09
# VERSION:     1.0.0
# REQUIRES:    Python 3.8+, selection_pool.py
# CHANGES:
#   2026-08-09: Initiale Implementierung für AP4
#               - compute_nutzwert() für Nutzwert-Berechnung
#               - sort_images_by_utility() für deterministische Sortierung
#               - assign_ranks() für dynamische Rangvergabe
# =============================================================================


import hashlib
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path


# =============================================================================
# Konstanten
# =============================================================================

# Gewichtung für Nutzwert
SCORE_WEIGHT = 0.6
RECENCY_WEIGHT = 0.3
DIVERSITY_WEIGHT = 0.1


# =============================================================================
# Nutzwert-Berechnung
# =============================================================================

def compute_recency_score(added_at: str, reference_date: Optional[str] = None) -> float:
    """
    Berechnet Recency-Score (0-1) basierend auf added_at.
    
    Args:
        added_at: ISO-8601 Datum (z.B. "2026-08-09T10:00:00Z")
        reference_date: Referenzdatum (default: heute)
    
    Returns:
        Recency-Score (0-1, 1 = sehr aktuell)
    """
    try:
        added = datetime.fromisoformat(added_at.replace("Z", "+00:00"))
        
        if reference_date:
            ref = datetime.fromisoformat(reference_date.replace("Z", "+00:00"))
        else:
            ref = datetime.utcnow().replace(tzinfo=added.tzinfo)
        
        # Differenz in Tagen
        delta_days = (ref - added).days
        
        # Exponentieller Abfall: nach 365 Tagen bei 0.5
        # recency = exp(-ln(2) * days / 365)
        import math
        recency = math.exp(-math.log(2) * max(0, delta_days) / 365)
        
        return min(1.0, max(0.0, recency))
    
    except (ValueError, TypeError):
        return 0.5  # Fallback bei unguel tigem Datum


def compute_diversity_score(image: Dict[str, Any], all_images: List[Dict[str, Any]]) -> float:
    """
    Berechnet Diversity-Score (0-1) basierend auf Embedding-Distanz.
    
    Args:
        image: Bild-Entry
        all_images: Alle Bilder im Pool
    
    Returns:
        Diversity-Score (0-1, 1 = sehr divers)
    
    TODO: Embedding-Distanz implementieren (AP6/CLIP)
    """
    # Placeholder: keine Embeddings verfügbar
    # Rückgabe: 0.5 (neutral)
    return 0.5


def compute_nutzwert(image: Dict[str, Any], all_images: List[Dict[str, Any]], 
                     reference_date: Optional[str] = None) -> float:
    """
    Berechnet Gesamtnutzwert (0-1) für ein Bild.
    
    Args:
        image: Bild-Entry
        all_images: Alle Bilder im Pool
        reference_date: Referenzdatum für Recency
    
    Returns:
        Nutzwert (0-1, 1 = bester Nutzwert)
    """
    # Score (0-1, default: 0.5 wenn nicht vorhanden)
    score = image.get("score", 0.5)
    
    # Recency (0-1)
    added_at = image.get("added_at", "")
    recency = compute_recency_score(added_at, reference_date) if added_at else 0.5
    
    # Diversity (0-1)
    diversity = compute_diversity_score(image, all_images)
    
    # Gewichteter Durchschnitt
    nutzwert = (
        score * SCORE_WEIGHT +
        recency * RECENCY_WEIGHT +
        diversity * DIVERSITY_WEIGHT
    )
    
    return min(1.0, max(0.0, nutzwert))


# =============================================================================
# Sortierung
# =============================================================================

def sort_images_by_utility(images: List[Dict[str, Any]], 
                           reference_date: Optional[str] = None) -> List[Tuple[Dict[str, Any], float]]:
    """
    Sortiert Bilder nach Nutzwert (deterministisch).
    
    Args:
        images: Liste von Bild-Entrys
        reference_date: Referenzdatum für Recency
    
    Returns:
        Liste von (image, nutzwert) Tupeln, sortiert nach:
        1. nutzwert absteigend
        2. added_at aufsteigend (aelteste zuerst)
        3. rel_path alphabetisch
    """
    # Nutzwert für jedes Bild berechnen
    scored_images = []
    for image in images:
        nutzwert = compute_nutzwert(image, images, reference_date)
        scored_images.append((image, nutzwert))
    
    # Sortieren
    def sort_key(item: Tuple[Dict[str, Any], float]) -> Tuple[float, str, str]:
        image, nutzwert = item
        added_at = image.get("added_at", "")
        rel_path = image.get("rel_path", "")
        
        # Sortierung:
        # 1. -nutzwert (absteigend)
        # 2. added_at (aufsteigend)
        # 3. rel_path (alphabetisch)
        return (-nutzwert, added_at, rel_path)
    
    sorted_images = sorted(scored_images, key=sort_key)
    
    return sorted_images


def assign_ranks(sorted_images: List[Tuple[Dict[str, Any], float]], 
                 rank_digits: int = 4) -> List[Dict[str, Any]]:
    """
    Weist dynamische Ranks zu (basierend auf sortierter Liste).
    
    Args:
        sorted_images: Sortierte Liste von (image, nutzwert)
        rank_digits: Anzahl der Stellen für Rank (default: 4)
    
    Returns:
        Liste von Bildern mit zugewiesenen Ranks
    """
    ranked_images = []
    
    for i, (image, nutzwert) in enumerate(sorted_images):
        rank = i + 1
        
        # Bild kopieren und Rank aktualisieren
        updated_image = dict(image)
        updated_image["rank"] = rank
        updated_image["_nutzwert"] = nutzwert  # Intern, für Debugging
        
        ranked_images.append(updated_image)
    
    return ranked_images


def reassign_ranks(images: List[Dict[str, Any]], rank_digits: int = 4,
                   reference_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Kombiniert sortieren und Ranks zuweisen.
    
    Args:
        images: Liste von Bild-Entrys
        rank_digits: Anzahl der Stellen für Rank
        reference_date: Referenzdatum für Recency
    
    Returns:
        Liste von Bildern mit neu zugewiesenen Ranks
    """
    sorted_images = sort_images_by_utility(images, reference_date)
    ranked_images = assign_ranks(sorted_images, rank_digits)
    return ranked_images